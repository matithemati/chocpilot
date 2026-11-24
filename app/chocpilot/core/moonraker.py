"""Klient Moonraker (API HTTP drukarek Klipper) – biblioteka standardowa, bez zależności.

Dokumentacja API: https://moonraker.readthedocs.io/en/latest/web_api/
Używane: /printer/info, /printer/objects/query, /printer/gcode/script, /printer/print/*,
/printer/emergency_stop, /printer/firmware_restart.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# Obiekty Klippera odczytywane do stanu drukarki.
STATUS_OBJECTS = (
    "print_stats",
    "display_status",
    "extruder",
    "heater_bed",
    "gcode_move",
    "toolhead",
    "fan",
)


class MoonrakerError(Exception):
    """Błąd połączenia lub odpowiedź błędu Moonrakera (komunikat do pokazania użytkownikowi)."""


@dataclass(frozen=True)
class PrinterStatus:
    online: bool = False
    state: str = "offline"  # ready/standby, printing, paused, complete, cancelled, error, shutdown
    message: str = ""
    filename: str = ""
    progress: float = 0.0  # 0–1
    nozzle: float = 0.0
    nozzle_target: float = 0.0
    bed: float = 0.0
    bed_target: float = 0.0
    speed_factor: float = 1.0  # M220 / 100
    flow_factor: float = 1.0  # M221 / 100
    z_offset: float = 0.0
    homed: str = ""  # np. "xyz"
    fan: float = 0.0  # 0–1

    @property
    def printing(self) -> bool:
        return self.state == "printing"

    @property
    def busy(self) -> bool:
        """Trwa wydruk (także wstrzymany) – ręczny ruch osi zablokowany."""
        return self.state in ("printing", "paused")


# (metoda, url, nagłówki, ciało, timeout) → (status HTTP, treść)
Transport = Callable[[str, str, dict[str, str], bytes | None, float], tuple[int, bytes]]


def _urllib_transport(
    method: str, url: str, headers: dict[str, str], body: bytes | None, timeout: float
) -> tuple[int, bytes]:
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def normalize_url(url: str) -> str:
    """„voron.local:7125” → „http://voron.local:7125” (bez końcowego ukośnika)."""
    url = url.strip().rstrip("/")
    if url and "://" not in url:
        url = "http://" + url
    return url


class MoonrakerClient:
    def __init__(
        self,
        url: str,
        api_key: str = "",
        timeout: float = 5.0,
        transport: Transport | None = None,
    ) -> None:
        self.url = normalize_url(url)
        self.api_key = api_key.strip()
        self.timeout = timeout
        self._transport = transport or _urllib_transport

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> Any:
        if not self.url:
            raise MoonrakerError("brak adresu drukarki")
        url = self.url + path
        if params:
            url += "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        try:
            status, body = self._transport(
                method, url, headers, b"" if method == "POST" else None, timeout or self.timeout
            )
        except (OSError, ValueError) as exc:  # brak sieci, timeout, zły adres
            raise MoonrakerError(f"brak połączenia ({exc})") from exc
        try:
            data = json.loads(body.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MoonrakerError(f"niepoprawna odpowiedź (HTTP {status})") from exc
        if status >= 400:
            error = data.get("error") if isinstance(data, dict) else None
            message = error.get("message") if isinstance(error, dict) else None
            if status in (401, 403):
                raise MoonrakerError("odmowa dostępu – sprawdź klucz API")
            raise MoonrakerError(str(message or f"HTTP {status}"))
        return data.get("result") if isinstance(data, dict) else None

    # ------------------------------------------------------------------ stan

    def status(self) -> PrinterStatus:
        info = self._request("GET", "/printer/info") or {}
        klippy_state = str(info.get("state", "unknown"))
        message = str(info.get("state_message", "")).strip().splitlines()
        if klippy_state != "ready":
            # Klipper nie działa (shutdown / error / startup) – obiekty niedostępne.
            return PrinterStatus(
                online=True, state=klippy_state, message=message[0] if message else ""
            )
        result = self._request("GET", "/printer/objects/query", {o: "" for o in STATUS_OBJECTS})
        s = (result or {}).get("status", {})

        def num(obj: str, key: str, default: float = 0.0) -> float:
            value = s.get(obj, {}).get(key, default)
            return float(value) if isinstance(value, int | float) else default

        stats = s.get("print_stats", {})
        origin = s.get("gcode_move", {}).get("homing_origin", [0, 0, 0, 0])
        return PrinterStatus(
            online=True,
            state=str(stats.get("state") or "standby"),
            message=str(stats.get("message") or ""),
            filename=str(stats.get("filename") or ""),
            progress=num("display_status", "progress"),
            nozzle=num("extruder", "temperature"),
            nozzle_target=num("extruder", "target"),
            bed=num("heater_bed", "temperature"),
            bed_target=num("heater_bed", "target"),
            speed_factor=num("gcode_move", "speed_factor", 1.0),
            flow_factor=num("gcode_move", "extrude_factor", 1.0),
            z_offset=float(origin[2]) if isinstance(origin, list) and len(origin) > 2 else 0.0,
            homed=str(s.get("toolhead", {}).get("homed_axes") or ""),
            fan=num("fan", "speed"),
        )

    # ------------------------------------------------------------------ polecenia

    def gcode(self, script: str, timeout: float = 120.0) -> None:
        """G-code / makro. Odpowiedź przychodzi po wykonaniu (G28 trwa – długi timeout)."""
        self._request("POST", "/printer/gcode/script", {"script": script}, timeout=timeout)

    def pause(self) -> None:
        self._request("POST", "/printer/print/pause")

    def resume(self) -> None:
        self._request("POST", "/printer/print/resume")

    def cancel(self) -> None:
        self._request("POST", "/printer/print/cancel")

    def emergency_stop(self) -> None:
        self._request("POST", "/printer/emergency_stop")

    def firmware_restart(self) -> None:
        self._request("POST", "/printer/firmware_restart")
