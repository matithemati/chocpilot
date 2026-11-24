"""Kontroler ChocPilot: zdarzenia z urządzenia → gesty → akcje; profil → ekran i tryb awaryjny.

Wszystko, co zmienia stan, dzieje się w jednym wątku pętli kontrolera (kolejka zdarzeń).
Akcje wykonują się w puli wątków (ActionExecutor). Testy mogą wywoływać
`handle_message()` i `tick()` bezpośrednio, z własnym zegarem.
"""

from __future__ import annotations

import datetime
import logging
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .. import __version__
from ..platform.base import PlatformBackend
from . import protocol
from .actions import ActionBase, ActionContext, ActionExecutor
from .actions.builtin import AppVolumeAction, LayerAction, MediaAction, ProfileAction
from .config import Config, ConfigStore, LedSettings, Profile, SliderBinding
from .fallback import compute_fallback
from .gestures import KEY_GESTURES, Gesture, GestureConfig, GestureEngine, GestureEvent
from .klipper import KlipperMode
from .moonraker import PrinterStatus
from .profiles import ForegroundWatcher, ProfileManager
from .protocol import (
    DeviceInfo,
    EncoderEvent,
    EncoderKeyEvent,
    ErrorEvent,
    KeyEvent,
    LogEvent,
    SliderEvent,
    TestModeEvent,
)
from .slider import SliderVolumeAction
from .transport import ConnectionState, Transport

log = logging.getLogger("chocpilot.engine")

SAVE_DELAY_S = 0.5


class ControllerListener:
    """Powiadomienia dla GUI (wołane z wątków roboczych – GUI musi przekazać do swojego)."""

    def connection_changed(
        self, connected: bool, info: DeviceInfo | None, port: str | None
    ) -> None:
        pass

    def raw_input(self, key: int, down: bool) -> None:
        """Fizyczne naciśnięcie / puszczenie klawisza 1–8."""

    def encoder_input(self, index: int, delta: int) -> None:
        """Obrót pokrętła 1–2 o `delta` zatrzasków."""

    def encoder_key_input(self, index: int, down: bool) -> None:
        """Przycisk pokrętła 1–2."""

    def slider_input(self, value: int) -> None:
        """Nowe położenie suwaka 0–100."""

    def gesture(self, event: GestureEvent, action: ActionBase | None) -> None:
        pass

    def profile_changed(self, profile: Profile, reason: str) -> None:
        pass

    def action_finished(self, summary: str, error: BaseException | None) -> None:
        pass

    def klipper_changed(self, active: bool, printer: str, status: PrinterStatus | None) -> None:
        pass

    def test_mode_changed(self, active: bool) -> None:
        pass


@dataclass
class _Task:
    kind: str
    payload: Any = None


class Controller:
    def __init__(
        self,
        config: Config,
        transport: Transport,
        platform: PlatformBackend,
        store: ConfigStore | None = None,
        executor: ActionExecutor | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config
        self.transport = transport
        self.platform = platform
        self.store = store
        self.clock = clock
        self.executor = executor or ActionExecutor(thread_init=platform.thread_init)
        self.listeners: list[ControllerListener] = []
        self.paused = False
        self.device_info: DeviceInfo | None = None

        self.profiles = ProfileManager(config)
        self.profiles.add_listener(self._on_profile_changed)
        self.gestures = GestureEngine(
            self._gesture_config(), emit=self._on_gesture, has_gesture=self._has_gesture
        )
        self._layer_keys: set[int] = set()
        # Suwak: najwyżej jedna zmiana głośności w toku, kolejna czeka tylko z najnowszą wartością.
        self._slider_busy = False
        self._slider_pending: int | None = None
        self._queue: queue.Queue[_Task] = queue.Queue()
        self._running = False
        self._thread: threading.Thread | None = None
        self._last_ping = 0.0
        self._last_time_sync: float | None = None
        # Tryb Klipper (drukarki 3D przez Moonraker) i przytrzymanie pokrętła, które go przełącza.
        self.klipper = KlipperMode(lambda: self.config.klipper, self, self.clock)
        self._toggle_hold: tuple[int, float, bool] | None = None  # (pokrętło, start, wykonane)
        # Ikony klawiszy: id ikony → 544 B dla urządzenia (ustawia GUI – biblioteka ikon).
        self.icon_payload: Callable[[str], bytes | None] | None = None
        self._sent_icons: dict[int, bytes | None] = {}
        # Czas lokalny do zegara na wygaszaczu (podmieniany w testach).
        self.local_time: Callable[[], datetime.datetime] = datetime.datetime.now
        self._save_due: float | None = None
        self._next_id = 1
        self._watcher = ForegroundWatcher(platform.foreground_process, self._on_foreground)

        transport.on_message = lambda message: self._queue.put(_Task("message", message))
        transport.on_state = lambda state, info, port: self._queue.put(
            _Task("state", (state, info, port))
        )

    # ------------------------------------------------------------------ cykl życia

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="chocpilot-engine", daemon=True)
        self._thread.start()
        self.transport.start()
        self._watcher.start()

    def stop(self) -> None:
        self._running = False
        self._watcher.stop()
        self._queue.put(_Task("stop"))
        self.transport.stop()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self.flush_save()
        self.klipper.stop()
        self.executor.shutdown()

    def _loop(self) -> None:
        while self._running:
            timeout = self._next_timeout()
            try:
                task = self._queue.get(timeout=timeout)
            except queue.Empty:
                task = None
            try:
                if task is not None:
                    self._handle_task(task)
                self.tick()
            except Exception:
                log.exception("Błąd w pętli kontrolera")

    def _next_timeout(self) -> float:
        now = self._now_ms()
        candidates = [protocol.PING_INTERVAL_S]
        deadline = self.gestures.next_deadline()
        if deadline is not None:
            candidates.append(max(0.0, (deadline - now) / 1000))
        if self._save_due is not None:
            candidates.append(max(0.0, self._save_due - self.clock()))
        return max(0.005, min(candidates))

    def _handle_task(self, task: _Task) -> None:
        if task.kind == "message":
            self.handle_message(task.payload)
        elif task.kind == "state":
            self.handle_state(*task.payload)
        elif task.kind == "call":
            task.payload()

    def call_soon(self, fn: Callable[[], object]) -> None:
        """Wykonaj funkcję w wątku kontrolera (np. z GUI)."""
        if self._running:
            self._queue.put(_Task("call", fn))
        else:
            fn()

    def _now_ms(self) -> float:
        return self.clock() * 1000

    # ------------------------------------------------------------------ zdarzenia z urządzenia

    def handle_state(
        self, state: ConnectionState, info: DeviceInfo | None, port: str | None
    ) -> None:
        if state == ConnectionState.CONNECTED:
            self.device_info = info
            self._reset_icons()
            self.gestures.reset()
            self.push_device_state()
            self._notify(lambda li: li.connection_changed(True, info, port))
        elif state == ConnectionState.DISCONNECTED:
            self.device_info = None
            self.gestures.reset()
            self._release_layers()
            self._notify(lambda li: li.connection_changed(False, None, None))

    def handle_message(self, message: dict[str, Any]) -> None:
        try:
            event = protocol.parse_device_message(message)
        except protocol.ProtocolError as exc:
            log.debug("Niepoprawna wiadomość od urządzenia: %s", exc)
            return
        now = self._now_ms()
        if isinstance(event, KeyEvent):
            self._notify(lambda li: li.raw_input(event.key, event.down))
            if self.klipper.active:
                self.klipper.on_key(event.key, event.down, self.clock())
            else:
                self._on_key(event.key, event.down, now)
        elif isinstance(event, DeviceInfo):
            # hello po restarcie urządzenia – wyślij stan ponownie
            if self.device_info is not None:
                self.device_info = event
                self._reset_icons()
                self.push_device_state()
        elif isinstance(event, ErrorEvent):
            log.warning("Urządzenie zgłosiło błąd (id=%s): %s", event.id, event.msg)
        elif isinstance(event, LogEvent):
            log.info("[urządzenie] %s", event.msg)
        elif isinstance(event, TestModeEvent):
            self._notify(lambda li: li.test_mode_changed(event.active))
        elif isinstance(event, EncoderEvent):
            self._notify(lambda li: li.encoder_input(event.index, event.delta))
            if self.klipper.active:
                self.klipper.on_encoder(event.index, event.delta)
            else:
                self._on_encoder(event)
        elif isinstance(event, EncoderKeyEvent):
            self._notify(lambda li: li.encoder_key_input(event.index, event.down))
            self._on_encoder_key(event.index, event.down)
        elif isinstance(event, SliderEvent):
            self._notify(lambda li: li.slider_input(event.value))
            if self.klipper.active:
                self.klipper.on_slider(event.value)
            else:
                self._on_slider(event.value)

    def _on_key(self, key: int, down: bool, now: float) -> None:
        if down:
            binding = self.profiles.effective.keys[key]
            layer = next((a for a in binding.actions() if isinstance(a, LayerAction)), None)
            if layer is not None:
                self._layer_keys.add(key)
                self.profiles.push_layer(key, layer.profile)
                return
            self.gestures.key_down(key, now)
        else:
            if key in self._layer_keys:
                self._layer_keys.discard(key)
                self.profiles.pop_layer(key)
                return
            self.gestures.key_up(key, now)

    def _on_encoder_key(self, index: int, down: bool) -> None:
        """Przycisk pokrętła. Pokrętło ustawione do przełączania trybu Klipper: przytrzymanie
        przełącza tryb (w tick), krótkie naciśnięcie działa zwykle – po puszczeniu."""
        trigger = {"e1_hold": 1, "e2_hold": 2}.get(self.config.klipper.toggle)
        if index == trigger:
            if down:
                self._toggle_hold = (index, self.clock(), False)
                return
            hold, self._toggle_hold = self._toggle_hold, None
            if hold is not None and not hold[2]:
                self._encoder_press(index)
            return
        if down:
            self._encoder_press(index)

    def _encoder_press(self, index: int) -> None:
        if self.klipper.active:
            self.klipper.on_encoder_press(index)
        else:
            self._run_encoder_action(index, "press", 1)

    def klipper_mode(self, mode: str) -> None:
        """Akcja „Klipper” (wątek akcji) – zmiana trybu w wątku kontrolera."""
        actions = {"enter": self.klipper.enter, "exit": self.klipper.exit}
        self.call_soon(actions.get(mode, self.klipper.toggle))

    def _reset_icons(self) -> None:
        """Po (ponownym) połączeniu stan ikon w urządzeniu jest nieznany – pierwsza synchronizacja
        wysyła ikony i czyści sloty bez ikony (mogły zostać z poprzedniej sesji aplikacji)."""
        self._sent_icons = {k: b"?" for k in range(1, protocol.KEY_COUNT + 1)}

    def sync_icons(self, icons: list[str]) -> None:
        """Wysyła tylko zmienione ikony klawiszy (płytki z `icon` w hello)."""
        if self.device_info is None or not self.device_info.icon_size:
            return
        for key, icon_id in enumerate(icons, start=1):
            payload = self.icon_payload(icon_id) if icon_id and self.icon_payload else None
            if self._sent_icons.get(key) == payload:
                continue
            if payload is None:
                self.send(protocol.msg_icon_clear(key))
            else:
                for message in protocol.msgs_icon(key, payload):
                    self.send(message)
            self._sent_icons[key] = payload

    def klipper_changed(self) -> None:
        printer = self.klipper.printer
        name = printer.name if printer else ""
        status = self.klipper.status
        active = self.klipper.active
        self._notify(lambda li: li.klipper_changed(active, name, status))

    def restore_display(self) -> None:
        self.send_profile_state()

    def _release_layers(self) -> None:
        self._layer_keys.clear()
        self.profiles.clear_layers()

    def tick(self) -> None:
        now = self.clock()
        self.gestures.tick(now * 1000)
        hold = self._toggle_hold
        if (
            hold is not None
            and not hold[2]
            and now - hold[1] >= self.config.klipper.toggle_ms / 1000
        ):
            self._toggle_hold = (hold[0], hold[1], True)
            self.klipper.toggle()
        self.klipper.tick(now)
        if self.transport.connected and now - self._last_ping >= protocol.PING_INTERVAL_S:
            self._last_ping = now
            self.transport.send(protocol.msg_ping())
        if (
            self._last_time_sync is not None
            and now - self._last_time_sync >= protocol.TIME_SYNC_INTERVAL_S
        ):
            self.send_time()
        if self._save_due is not None and now >= self._save_due:
            self.flush_save()

    def send_time(self) -> None:
        """Czas lokalny dla zegara na wygaszaczu – po połączeniu i co kilka minut (zmiana czasu
        letniego / dryf zegara płytki); tylko płytki z animowanym wygaszaczem (LCD)."""
        if self.device_info is None or not self.device_info.savers:
            self._last_time_sync = None
            return
        t = self.local_time()
        self.send(protocol.msg_time(t.hour, t.minute, t.second))
        self._last_time_sync = self.clock()

    # ------------------------------------------------------------------ gesty i akcje

    def _gesture_config(self) -> GestureConfig:
        g = self.config.settings.gestures
        return GestureConfig(
            hold_ms=g.hold_ms,
            double_tap_ms=g.double_tap_ms,
            hold_on_threshold=g.hold_on_threshold,
        )

    def _has_gesture(self, key: int, gesture: Gesture) -> bool:
        return self.profiles.effective.action_for(key, gesture) is not None

    def _on_gesture(self, event: GestureEvent) -> None:
        profile = self.profiles.effective
        action = profile.action_for(event.key, event.gesture)
        self._notify(lambda li: li.gesture(event, action))
        if action is None or isinstance(action, LayerAction):
            return
        if self.paused:
            log.info("Akcje wstrzymane – pominięto %s", action.summary())
            return
        label = profile.keys[event.key].label if event.key is not None else ""
        ctx = ActionContext(self.platform, self, steps=event.steps, key=event.key)
        ctx.extra["label"] = label
        ctx.extra["gesture"] = event.gesture
        log.info("%s %s → %s", _key_name(event.key), event.gesture, action.summary())
        self.executor.submit(action, ctx, self._after_action)

    def _after_action(
        self, action: ActionBase, ctx: ActionContext, error: BaseException | None
    ) -> None:
        self._notify(lambda li: li.action_finished(action.summary(), error))
        if error is not None:
            if ctx.key is not None:
                self.send(protocol.msg_flash("Blad!", ctx.key, 1000))
            return
        if (
            not self.config.settings.app.flash_on_action
            or ctx.key is None
            or ctx.extra.get("gesture") not in KEY_GESTURES
            or isinstance(action, ProfileAction | MediaAction | AppVolumeAction)
        ):
            return
        text = ctx.extra.get("label") or action.summary()
        self.send(protocol.msg_flash(text, ctx.key, 800))

    # ------------------------------------------------------------------ pokrętła i suwak

    def _on_encoder(self, event: EncoderEvent) -> None:
        gesture = "cw" if event.delta > 0 else "ccw"
        self._run_encoder_action(event.index, gesture, abs(event.delta))

    def _run_encoder_action(self, index: int, gesture: str, steps: int) -> None:
        binding = self.profiles.effective.encoders.get(index)
        action = binding.action_for(gesture) if binding is not None else None
        if action is None or isinstance(action, LayerAction):
            return
        if self.paused:
            log.info("Akcje wstrzymane – pominięto %s", action.summary())
            return
        # Akcje z `encoder_repeat` (skrót, tekst…) wykonują się `steps` razy, głośność
        # i przewijanie mnożą krok przez liczbę zatrzasków.
        ctx = ActionContext(self.platform, self, steps=steps, key=None)
        ctx.extra["label"] = binding.label if binding is not None else ""
        ctx.extra["gesture"] = f"E{index}:{gesture}"
        log.debug("E%s %s ×%s → %s", index, gesture, steps, action.summary())
        self.executor.submit(action, ctx, self._after_action)

    def _on_slider(self, value: int) -> None:
        if self.profiles.effective.slider.target == "off" or self.paused:
            return
        if self._slider_busy:
            self._slider_pending = value
            return
        self._submit_slider(value)

    def _submit_slider(self, value: int) -> None:
        binding: SliderBinding = self.profiles.effective.slider
        if binding.target == "off":
            return
        self._slider_busy = True
        action = SliderVolumeAction(
            target=binding.target, process=binding.process, label_text=binding.label, value=value
        )
        ctx = ActionContext(self.platform, self, steps=1, key=None)
        self.executor.submit(action, ctx, self._after_slider)

    def _after_slider(
        self, action: ActionBase, ctx: ActionContext, error: BaseException | None
    ) -> None:
        if error is not None:
            self._notify(lambda li: li.action_finished(action.summary(), error))
        self.call_soon(self._slider_done)

    def _slider_done(self) -> None:
        self._slider_busy = False
        if self._slider_pending is not None:
            value, self._slider_pending = self._slider_pending, None
            self._submit_slider(value)

    def test_action(self, action: ActionBase, key: int | None = None) -> None:
        """Wykonanie akcji z GUI (przycisk „Testuj”)."""
        ctx = ActionContext(self.platform, self, steps=1, key=key)
        ctx.extra["gesture"] = Gesture.TAP
        self.executor.submit(action, ctx, self._after_action)

    # ------------------------------------------------------------------ ActionHost

    def switch_profile(self, name: str) -> None:
        self.profiles.set_active(name, "manual")

    def next_profile(self) -> None:
        self.profiles.next()

    def prev_profile(self) -> None:
        self.profiles.prev()

    def show_bar(self, title: str, value: float) -> None:
        self.send(protocol.msg_display_bar(title, value, 1500))

    def show_text(self, line1: str, line2: str = "", ms: int = 1500) -> None:
        self.send(protocol.msg_display_text(line1, line2, ms))

    # ------------------------------------------------------------------ wysyłanie stanu

    def send(self, message: dict[str, Any], with_id: bool = False) -> bool:
        if with_id:
            message = {**message, "id": self._next_id}
            self._next_id += 1
        return self.transport.send(message)

    def push_device_state(self) -> None:
        """Ustawienia + LED + ekran + skróty awaryjne (po połączeniu i po zmianach)."""
        self.send_settings()
        self.send_time()
        self.send_leds(profile_color=False)
        self.send_profile_state()

    @property
    def has_leds(self) -> bool:
        return self.device_info is not None and self.device_info.leds > 0

    def send_leds(self, profile_color: bool = True) -> None:
        """Ustawienia LED z zapisem w urządzeniu (+ kolor aktywnego profilu bez zapisu)."""
        if not self.has_leds:
            return
        led = self.config.settings.device.leds
        self.send(
            protocol.msg_leds(
                mode=led.mode,
                color=led.color,
                brightness=led.brightness,
                speed=led.speed,
                react=led.react,
            ),
            with_id=True,
        )
        if profile_color:
            self._send_profile_led_color()

    def _send_profile_led_color(self) -> None:
        """Kolor aktywnego profilu (albo z ustawień) – bez zapisu, żeby nie zużywać pamięci."""
        if not self.has_leds:
            return
        color = self.profiles.effective.led_color or self.config.settings.device.leds.color
        self.send(protocol.msg_leds(color=color, save=False))

    def preview_leds(self, led: LedSettings) -> None:
        """Podgląd na żywo z okna ustawień (bez zapisu – Anuluj przywraca restore_leds)."""

        def apply() -> None:
            if self.has_leds:
                self.send(
                    protocol.msg_leds(
                        mode=led.mode,
                        color=led.color,
                        brightness=led.brightness,
                        speed=led.speed,
                        react=led.react,
                        save=False,
                    )
                )

        self.call_soon(apply)

    def restore_leds(self) -> None:
        """Wysyła ponownie zapisane ustawienia LED (po anulowaniu podglądu)."""
        self.call_soon(self.send_leds)

    def send_settings(self) -> None:
        d = self.config.settings.device
        values: dict[str, Any] = {
            "brightness": d.brightness,
            "screensaver_s": d.screensaver_s,
            "flip": d.flip,
            "debounce_ms": d.debounce_ms,
        }
        if self.device_info is not None and self.device_info.savers:
            # Nieznana urządzeniu animacja (np. z innej płytki) → wygaszony ekran.
            ok = d.saver in self.device_info.savers
            values["saver"] = d.saver if ok else protocol.SAVER_OFF
        self.send(protocol.msg_settings(**values), with_id=True)

    def send_profile_state(self, flash_name: bool = False) -> None:
        profile = self.profiles.effective
        if self.klipper.active:
            self.klipper.refresh_display()  # ekran trybu Klipper (etykiety i ikony) zamiast profilu
        elif self.config.settings.device.display_mode == "profile":
            self.send(protocol.msg_display_profile(profile.name))
        else:
            # Ikony przed siatką: pierwsze rysowanie nowej siatki ma już wszystkie ikony.
            self.sync_icons(profile.icons())
            self.send(protocol.msg_display_grid(profile.name, profile.labels()))
            if flash_name:
                self.send(protocol.msg_flash(profile.name, None, 400))
        self._send_profile_led_color()
        bindings = compute_fallback(self.profiles.active, self.config.settings.fallback)
        max_line = self.device_info.max_line if self.device_info else protocol.MAX_LINE_LENGTH
        for message in protocol.msgs_set_fallback(bindings, max_line):
            self.send(message, with_id=True)

    def _on_profile_changed(self, profile: Profile, reason: str) -> None:
        self.send_profile_state(flash_name=reason in ("manual", "auto", "auto-return"))
        self._notify(lambda li: li.profile_changed(profile, reason))

    def _on_foreground(self, exe: str | None) -> None:
        self.call_soon(lambda: self.profiles.on_foreground(exe))

    # ------------------------------------------------------------------ zmiany konfiguracji

    def config_changed(self, device_settings: bool = False) -> None:
        """Wywoływane przez GUI po edycji konfiguracji."""

        def apply() -> None:
            self.gestures.config = self._gesture_config()
            self.profiles.refresh()  # wysyła display + set_fallback
            if device_settings:
                self.send_settings()
                self.send_leds()  # pełne ustawienia nadpisują kolor – profilowy wysyłany ponownie
            self.schedule_save()

        self.call_soon(apply)

    def schedule_save(self) -> None:
        self._save_due = self.clock() + SAVE_DELAY_S
        if not self._running:
            self.flush_save()

    def flush_save(self) -> None:
        self._save_due = None
        if self.store is None:
            return
        try:
            self.store.save(self.config)
        except OSError as exc:
            log.error("Nie zapisano konfiguracji: %s", exc)

    def set_test_mode(self, enable: bool) -> None:
        self.send(protocol.msg_test_mode(enable))

    def reboot_device(self, bootloader: bool = False) -> None:
        self.send(protocol.msg_reboot(bootloader), with_id=True)

    # ------------------------------------------------------------------ pomocnicze

    def add_listener(self, listener: ControllerListener) -> None:
        self.listeners.append(listener)

    def _notify(self, fn: Callable[[ControllerListener], None]) -> None:
        for listener in list(self.listeners):
            try:
                fn(listener)
            except Exception:
                log.exception("Błąd słuchacza kontrolera")


def _key_name(key: int) -> str:
    return f"K{key}"


__all__ = ["Controller", "ControllerListener", "__version__"]
