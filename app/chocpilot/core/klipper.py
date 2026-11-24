"""Tryb Klipper: macropad steruje drukarką 3D (Klipper przez Moonraker).

W trybie Klipper zdarzenia z urządzenia trafiają tutaj zamiast do akcji profilu:
- klawisze K1–K8: polecenia z ustawień (G-code/makro, pauza/wznowienie, anuluj, awaryjne
  zatrzymanie…); niebezpieczne wymagają przytrzymania,
- pokrętło E1: ruch osi (naciśnięcie zmienia X → Y → Z); w trakcie wydruku – Z offset (babystep),
- pokrętło E2: temperatura dyszy/stołu, prędkość, przepływ, wentylator (naciśnięcie zmienia),
- suwak: wentylator albo prędkość wydruku,
- ekran: nazwa drukarki, stan i temperatury w tytule, etykiety klawiszy w siatce.

Żądania HTTP idą w jednym wątku roboczym (KlipperWorker). Zadania z kluczem (np. „nozzle”)
zastępują jeszcze niewysłane – szybkie kręcenie pokrętłem wysyła tylko najnowszą wartość.
"""

from __future__ import annotations

import logging
import threading
from collections import OrderedDict
from collections.abc import Callable, Hashable
from typing import Any, Protocol

from . import protocol
from .config import KlipperKey, KlipperPrinter, KlipperSettings
from .moonraker import MoonrakerClient, MoonrakerError, PrinterStatus

log = logging.getLogger(__name__)

AXES = ("X", "Y", "Z")
# Krótkie nazwy na ekran (bez polskich znaków – ekran ma krój ASCII).
PARAM_NAMES = {
    "nozzle": "Dysza",
    "bed": "Stol",
    "speed": "Predkosc",
    "flow": "Przeplyw",
    "fan": "Wentylator",
}
PARAM_UNITS = {"nozzle": "C", "bed": "C", "speed": "%", "flow": "%", "fan": "%"}
PARAM_LIMITS = {
    "nozzle": (0, 350),
    "bed": (0, 150),
    "speed": (10, 300),
    "flow": (50, 200),
    "fan": (0, 100),
}
STATE_TEXT = {
    "paused": "PAUZA",
    "complete": "koniec",
    "cancelled": "anul.",
    "error": "BLAD",
    "standby": "gotowa",
    "ready": "gotowa",
    "shutdown": "STOP",
    "startup": "start",
}


class KlipperHost(Protocol):
    """Usługi kontrolera dla trybu Klipper."""

    def send(self, message: dict[str, Any], with_id: bool = False) -> bool: ...
    def call_soon(self, fn: Callable[[], object]) -> None: ...
    def klipper_changed(self) -> None: ...
    def restore_display(self) -> None: ...
    def sync_icons(self, icons: list[str]) -> None: ...


class KlipperWorker:
    """Jeden wątek na żądania do drukarek; zadanie z tym samym kluczem zastępuje oczekujące."""

    def __init__(self, sync: bool = False) -> None:
        self._sync = sync  # testy: zadanie wykonuje się od razu
        self._jobs: OrderedDict[Hashable, Callable[[], None]] = OrderedDict()
        self._cond = threading.Condition()
        self._thread: threading.Thread | None = None
        self._stopped = False
        self._seq = 0

    def submit(self, fn: Callable[[], None], key: Hashable | None = None) -> None:
        if self._sync:
            fn()
            return
        with self._cond:
            if key is None:
                self._seq += 1
                key = ("job", self._seq)
            self._jobs[key] = fn  # istniejący klucz: nowa funkcja, kolejność bez zmian
            if self._thread is None or not self._thread.is_alive():
                self._stopped = False
                self._thread = threading.Thread(target=self._run, name="klipper", daemon=True)
                self._thread.start()
            self._cond.notify()

    def stop(self) -> None:
        with self._cond:
            self._stopped = True
            self._jobs.clear()
            self._cond.notify()

    def _run(self) -> None:
        while True:
            with self._cond:
                while not self._jobs and not self._stopped:
                    self._cond.wait()
                if self._stopped:
                    return
                _, fn = self._jobs.popitem(last=False)
            try:
                fn()
            except Exception:  # błąd jednego zadania nie zatrzymuje wątku
                log.exception("Klipper: błąd zadania")


class KlipperMode:
    def __init__(
        self,
        settings: Callable[[], KlipperSettings],
        host: KlipperHost,
        clock: Callable[[], float],
        client_factory: Callable[[str, str], MoonrakerClient] = MoonrakerClient,
        worker: KlipperWorker | None = None,
    ) -> None:
        self._settings = settings
        self.host = host
        self.clock = clock
        self._client_factory = client_factory
        self.worker = worker or KlipperWorker()
        self.active = False
        self.status: PrinterStatus | None = None
        self.axis = 0
        self.param = 0
        self._held: dict[int, float] = {}  # klawisz z „wymaga przytrzymania” → czas naciśnięcia
        self._fired: set[int] = set()
        self._last_poll = 0.0
        self._lock = threading.Lock()  # oczekujące wartości czytane przez wątek roboczy
        self._targets: dict[str, float] = {}  # nastawy E2 jeszcze niepotwierdzone przez stan
        self._jog: dict[str, float] = {}  # ruch osi do wysłania
        self._babystep = 0.0

    @property
    def settings(self) -> KlipperSettings:
        return self._settings()

    # ------------------------------------------------------------------ drukarki

    @property
    def printer_index(self) -> int:
        printers = self.settings.printers
        if not printers:
            return 0
        return min(max(self.settings.active_printer, 0), len(printers) - 1)

    @property
    def printer(self) -> KlipperPrinter | None:
        printers = self.settings.printers
        return printers[self.printer_index] if printers else None

    def client(self, printer: KlipperPrinter | None = None) -> MoonrakerClient:
        p = printer or self.printer
        if p is None:
            raise MoonrakerError("brak drukarki")
        return self._client_factory(p.url, p.api_key)

    def select_printer(self, index: int) -> None:
        printers = self.settings.printers
        if not printers:
            return
        self.settings.active_printer = index % len(printers)
        with self._lock:
            self._targets.clear()
            self._jog.clear()
            self._babystep = 0.0
        self.status = None
        if self.active:
            self.refresh_display()
            self.poll()
        self.host.klipper_changed()

    # ------------------------------------------------------------------ tryb

    def toggle(self) -> None:
        if self.active:
            self.exit()
        else:
            self.enter()

    def enter(self) -> None:
        if self.active:
            return
        if self.printer is None:
            self._show("Klipper", "brak drukarek", 2000)
            log.info("Tryb Klipper: brak skonfigurowanych drukarek")
            return
        self.active = True
        self._held.clear()
        self._fired.clear()
        log.info("Tryb Klipper: włączony (%s)", self.printer.name)
        self.host.send(protocol.msg_flash("Klipper", None, 400))
        self.refresh_display()
        self.poll()
        self.host.klipper_changed()

    def exit(self) -> None:
        if not self.active:
            return
        self.active = False
        self._held.clear()
        log.info("Tryb Klipper: wyłączony")
        self.host.restore_display()
        self.host.klipper_changed()

    # ------------------------------------------------------------------ ekran

    def title(self) -> str:
        p = self.printer
        name = p.name if p else "Klipper"
        st = self.status
        if st is None:
            return f"{name} ..."
        if not st.online:
            return f"{name} offline"
        state = f"{st.progress * 100:.0f}%" if st.printing else STATE_TEXT.get(st.state, st.state)
        if st.state in ("shutdown", "error", "startup"):
            return f"{name} {state}"
        return f"{name} {state} {st.nozzle:.0f}/{st.bed:.0f}"

    def labels(self) -> list[str]:
        out = []
        for k in range(1, len(self.settings.keys) + 1):
            key = self.settings.keys[k]
            label = key.label
            if key.command == "pause_resume" and self.status is not None:
                label = "Wznow" if self.status.state == "paused" else (label or "Pauza")
            out.append(label)
        return out

    def icons(self) -> list[str]:
        """Ikony klawiszy; domyślna ikona pauzy pokazuje, co zrobi klawisz (wznów / wstrzymaj)."""
        out = []
        for k in range(1, len(self.settings.keys) + 1):
            key = self.settings.keys[k]
            icon = key.icon
            if key.command == "pause_resume" and icon == "builtin:play-pause" and self.status:
                if self.status.state == "paused":
                    icon = "builtin:play"
                elif self.status.printing:
                    icon = "builtin:pause"
            out.append(icon)
        return out

    def refresh_display(self) -> None:
        self.host.sync_icons(self.icons())  # ikony przed siatką – jedno rysowanie z ikonami
        self.host.send(protocol.msg_display_grid(self.title(), self.labels()))

    def _show(self, line1: str, line2: str = "", ms: int = 1200) -> None:
        self.host.send(protocol.msg_display_text(line1, line2, ms))

    # ------------------------------------------------------------------ stan drukarki

    def tick(self, now: float) -> None:
        if not self.active:
            return
        hold_s = self.settings.hold_ms / 1000
        for key, start in list(self._held.items()):
            if key not in self._fired and now - start >= hold_s:
                self._fired.add(key)
                self._execute(key, self.settings.keys[key])
        if now - self._last_poll >= self.settings.poll_s:
            self.poll()

    def poll(self) -> None:
        printer = self.printer
        if printer is None:
            return
        self._last_poll = self.clock()
        index = self.printer_index
        client = self.client(printer)

        def fetch() -> None:
            try:
                status = client.status()
            except MoonrakerError as exc:
                status = PrinterStatus(online=False, message=str(exc))
            self.host.call_soon(lambda: self._apply_status(index, status))

        self.worker.submit(fetch, key="status")

    def _apply_status(self, index: int, status: PrinterStatus) -> None:
        if index != self.printer_index:
            return  # odpowiedź od poprzednio wybranej drukarki
        changed = status != self.status
        self.status = status
        with self._lock:
            for name in list(self._targets):  # nastawa potwierdzona przez drukarkę
                current = self._param_value(name, status)
                if current is not None and abs(current - self._targets[name]) < 0.6:
                    del self._targets[name]
        if changed:
            if self.active:
                self.refresh_display()
            self.host.klipper_changed()

    def test_connection(
        self, printer: KlipperPrinter, done: Callable[[PrinterStatus], None]
    ) -> None:
        """Test z ustawień: stan drukarki do callbacku (w wątku kontrolera)."""
        client = self.client(printer)

        def fetch() -> None:
            try:
                status = client.status()
            except MoonrakerError as exc:
                status = PrinterStatus(online=False, message=str(exc))
            self.host.call_soon(lambda: done(status))

        self.worker.submit(fetch)

    def _run(self, fn: Callable[[MoonrakerClient], None], key: Hashable | None = None) -> None:
        """Polecenie do drukarki w wątku roboczym; błąd na ekran, po sukcesie odświeżenie stanu."""
        try:
            client = self.client()
        except MoonrakerError as exc:
            self._show("Klipper", str(exc), 2000)
            return

        def job() -> None:
            try:
                fn(client)
            except MoonrakerError as exc:
                message = str(exc)
                log.warning("Klipper: %s", message)
                self.host.call_soon(lambda: self._show("Blad Klipper", message, 2500))
                return
            self.host.call_soon(self.poll)

        self.worker.submit(job, key)

    # ------------------------------------------------------------------ klawisze

    def on_key(self, key: int, down: bool, now: float) -> None:
        binding = self.settings.keys.get(key)
        if binding is None:
            return
        if down:
            if binding.hold:
                self._held[key] = now
            else:
                self._execute(key, binding)
            return
        start = self._held.pop(key, None)
        if start is not None and key not in self._fired:
            seconds = self.settings.hold_ms / 1000
            self._show(f"Przytrzymaj {seconds:.1f}s", binding.label or "klawisz", 1200)
        self._fired.discard(key)

    def _execute(self, key: int, binding: KlipperKey) -> None:
        command = binding.command
        label = binding.label
        st = self.status
        log.info("Klipper K%s: %s", key, command if command != "gcode" else binding.gcode)
        if command == "gcode":
            script = binding.gcode.strip()
            if not script:
                self._show(label or f"K{key}", "brak G-code", 1500)
                return
            self.host.send(protocol.msg_flash(label or "G-code", key, 800))
            self._run(lambda c: c.gcode(script))
        elif command == "pause_resume":
            if st is not None and st.state == "paused":
                self.host.send(protocol.msg_flash("Wznow", key, 800))
                self._run(lambda c: c.resume())
            elif st is not None and st.printing:
                self.host.send(protocol.msg_flash("Pauza", key, 800))
                self._run(lambda c: c.pause())
            else:
                self._show("Nie drukuje", "", 1200)
        elif command == "cancel":
            if st is not None and st.busy:
                self.host.send(protocol.msg_flash("Anulowano", key, 1000))
                self._run(lambda c: c.cancel())
            else:
                self._show("Nie drukuje", "", 1200)
        elif command == "estop":
            self.host.send(protocol.msg_flash("STOP!", key, 1500))
            self._run(lambda c: c.emergency_stop())
        elif command == "firmware_restart":
            self.host.send(protocol.msg_flash("Restart FW", key, 1000))
            self._run(lambda c: c.firmware_restart())
        elif command == "next_printer":
            if len(self.settings.printers) < 2:
                self._show(self.printer.name if self.printer else "Klipper", "jedyna drukarka")
                return
            self.select_printer(self.printer_index + 1)
            self.host.send(protocol.msg_flash(self.printer.name if self.printer else "", key, 900))
        elif command == "exit":
            self.exit()

    # ------------------------------------------------------------------ pokrętła i suwak

    def on_encoder_press(self, index: int) -> None:
        if index == 1:
            self.axis = (self.axis + 1) % len(AXES)
            self._show(f"Ruch: {AXES[self.axis]}", "pokretlo E1", 1000)
        elif index == 2:
            params = self.settings.params
            self.param = (self.param + 1) % len(params)
            self._show(PARAM_NAMES[params[self.param]], "pokretlo E2", 1000)

    def on_encoder(self, index: int, delta: int) -> None:
        if index == 1:
            self._jog_or_babystep(delta)
        elif index == 2:
            params = self.settings.params
            self._adjust(params[self.param % len(params)], delta)

    def _ready_status(self) -> PrinterStatus | None:
        st = self.status
        if st is None:
            self._show("Klipper", "czekam na stan", 1000)
            return None
        if not st.online or st.state in ("shutdown", "error", "startup"):
            self._show("Klipper", "offline" if not st.online else st.state, 1500)
            return None
        return st

    def _jog_or_babystep(self, delta: int) -> None:
        st = self._ready_status()
        if st is None:
            return
        s = self.settings
        if st.busy:
            # W trakcie wydruku: Z offset w locie (ruch osi byłby niebezpieczny).
            with self._lock:
                self._babystep += delta * s.babystep
                total = self._babystep

            def babystep(c: MoonrakerClient) -> None:
                with self._lock:
                    amount, self._babystep = self._babystep, 0.0
                if abs(amount) > 1e-9:
                    c.gcode(f"SET_GCODE_OFFSET Z_ADJUST={amount:+.3f} MOVE=1")

            self._show("Z offset", f"{st.z_offset + total:+.3f} mm", 1000)
            self._run(babystep, key="babystep")
            return
        axis = AXES[self.axis]
        if axis.lower() not in st.homed.lower():
            self._show("Najpierw Home", f"os {axis}", 1500)
            return
        step = s.jog_z if axis == "Z" else s.jog_xy
        with self._lock:
            self._jog[axis] = self._jog.get(axis, 0.0) + delta * step
            pending = self._jog[axis]

        def jog(c: MoonrakerClient) -> None:
            with self._lock:
                moves, self._jog = dict(self._jog), {}
            parts = " ".join(f"{a}{d:+.3f}" for a, d in moves.items() if abs(d) > 1e-9)
            if parts:
                c.gcode(f"G91\nG1 {parts} F{s.jog_feed}\nG90")

        self._show(f"{axis} {pending:+.2f} mm", "ruch osi", 800)
        self._run(jog, key="jog")

    @staticmethod
    def _param_value(name: str, st: PrinterStatus) -> float | None:
        return {
            "nozzle": st.nozzle_target,
            "bed": st.bed_target,
            "speed": st.speed_factor * 100,
            "flow": st.flow_factor * 100,
            "fan": st.fan * 100,
        }.get(name)

    def _adjust(self, name: str, delta: int) -> None:
        st = self._ready_status()
        if st is None:
            return
        step = {"nozzle": self.settings.temp_step, "bed": self.settings.temp_step}.get(
            name, {"speed": 5, "flow": 1, "fan": 5}.get(name, 1)
        )
        lo, hi = PARAM_LIMITS[name]
        with self._lock:
            base = self._targets.get(name)
            if base is None:
                base = self._param_value(name, st) or 0.0
            value = float(min(hi, max(lo, round(base) + delta * step)))
            self._targets[name] = value

        def apply(c: MoonrakerClient) -> None:
            with self._lock:
                target = self._targets.get(name, value)
            c.gcode(_param_gcode(name, target))

        self._show(f"{PARAM_NAMES[name]} {value:.0f}{PARAM_UNITS[name]}", "nastawa", 1000)
        self._run(apply, key=("param", name))

    def on_slider(self, value: int) -> None:
        target = self.settings.slider
        if target == "off":
            return
        if target == "fan":
            title, gcode = f"Wentylator {value}%", f"M106 S{_fan_pwm(value)}"
        else:  # prędkość 50–150 %
            percent = 50 + value
            title, gcode = f"Predkosc {percent}%", f"M220 S{percent}"
        self.host.send(protocol.msg_display_bar(title, value, 800))
        self._run(lambda c: c.gcode(gcode), key="slider")

    def stop(self) -> None:
        self.worker.stop()


def _fan_pwm(percent: float) -> int:
    """0–100 % → 0–255 (liczby całkowite: 50 % = 128, bez błędu zaokrąglenia 2,55)."""
    return (min(100, max(0, round(percent))) * 255 + 50) // 100


def _param_gcode(name: str, value: float) -> str:
    if name == "nozzle":
        return f"M104 S{value:.0f}"
    if name == "bed":
        return f"M140 S{value:.0f}"
    if name == "speed":
        return f"M220 S{value:.0f}"
    if name == "flow":
        return f"M221 S{value:.0f}"
    return f"M106 S{_fan_pwm(value)}"
