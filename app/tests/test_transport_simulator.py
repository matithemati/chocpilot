"""Transport szeregowy (atrapa portu), wykrywanie portów i symulator urządzenia."""

from __future__ import annotations

import queue
import time
from dataclasses import dataclass
from typing import Any

from chocpilot.core import protocol
from chocpilot.core.simulator import SimulatedDevice, SimulatorTransport
from chocpilot.core.transport import ConnectionState, SerialTransport, candidate_ports
from tests.conftest import ManualClock


@dataclass
class PortInfo:
    device: str
    vid: int | None = None
    pid: int | None = None
    product: str | None = None
    manufacturer: str | None = None
    description: str | None = None


def test_candidate_ports_prefers_product_name() -> None:
    ports = [
        PortInfo("COM1", vid=0x1234, description="Bluetooth"),
        PortInfo("COM5", vid=0x1B4F, pid=0x9206, description="USB Serial Device"),
        PortInfo("COM9", vid=0x1B4F, pid=0x9206, product="ChocPilot"),
        PortInfo("COM7", vid=0x303A),  # ESP32 – nie ChocPilot
    ]
    assert candidate_ports(ports) == ["COM9", "COM5"]


def test_candidate_ports_pro_micro_only_application_pids() -> None:
    ports = [
        PortInfo("COM4", vid=0x1B4F, pid=0x9206),  # Pro Micro 5 V (program)
        PortInfo("COM5", vid=0x1B4F, pid=0x9205),  # bootloader Caterina – pomijany
        PortInfo("COM6", vid=0x2341, pid=0x0043),  # Arduino Uno – pomijane (reset po otwarciu)
        PortInfo("COM8", vid=0x2341, pid=0x8036),  # klon z bootloaderem Leonardo
    ]
    assert candidate_ports(ports) == ["COM4", "COM8"]


class FakeSerial:
    """Port szeregowy połączony z SimulatedDevice."""

    def __init__(self, device: SimulatedDevice) -> None:
        self.device = device
        self.rx: queue.Queue[bytes] = queue.Queue()
        device.emit = lambda msg: self.rx.put(protocol.encode(msg))
        self.port = ""
        self.is_open = False
        self.broken = False

    def open(self) -> None:
        if self.port != "COM9":
            raise OSError("no such port")
        self.is_open = True

    def close(self) -> None:
        self.is_open = False

    def reset_input_buffer(self) -> None:
        pass

    def write(self, data: bytes) -> int:
        if self.broken:
            raise OSError("unplugged")
        for line in data.splitlines():
            self.device.handle_line(line)
        return len(data)

    def readline(self) -> bytes:
        if self.broken:
            raise OSError("unplugged")
        try:
            return self.rx.get(timeout=0.02)
        except queue.Empty:
            return b""


def wait_for(predicate, timeout: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_serial_transport_detects_and_reconnects() -> None:
    device = SimulatedDevice()
    serials: list[FakeSerial] = []

    def factory() -> FakeSerial:
        s = FakeSerial(device)
        serials.append(s)
        return s

    transport = SerialTransport(
        serial_factory=factory,
        port_lister=lambda: ["COM3", "COM9"],
        hello_timeout=0.5,
        retry_interval=0.05,
    )
    states: list[ConnectionState] = []
    messages: list[dict[str, Any]] = []
    transport.on_state = lambda state, info, port: states.append(state)
    transport.on_message = messages.append
    transport.start()
    try:
        assert wait_for(lambda: transport.connected)
        assert transport.port_name == "COM9"
        assert transport.device_info is not None
        assert transport.device_info.board_name == "Pro Micro"
        assert device.online

        device.press(3)
        assert wait_for(lambda: any(m.get("type") == "key" for m in messages))

        # Odłączenie kabla → rozłączenie → ponowne połączenie
        serials[-1].broken = True
        assert wait_for(lambda: ConnectionState.DISCONNECTED in states)
        assert wait_for(lambda: transport.connected and len(serials) >= 3)
    finally:
        transport.stop()


def test_simulated_device_protocol() -> None:
    clock = ManualClock()
    out: list[dict[str, Any]] = []
    device = SimulatedDevice(clock=clock, emit=out.append)
    clock.advance(2)
    assert device.screen().kind == "offline"

    device.handle({"type": "hello", "app": "x"})
    assert out[-1]["type"] == "hello" and out[-1]["device"] == "chocpilot"
    assert device.online

    device.handle({"type": "display", "mode": "grid", "title": "T", "labels": ["a", "b"], "id": 4})
    assert out[-1] == {"type": "ack", "id": 4}
    screen = device.screen()
    assert screen.kind == "grid" and screen.labels[:2] == ("a", "b") and screen.online

    device.handle({"type": "display", "mode": "bar", "title": "Vol", "value": 30, "ms": 500})
    assert device.screen().kind == "bar"
    clock.advance(0.6)
    device.handle({"type": "ping"})
    assert device.screen().kind == "grid"

    device.handle({"type": "settings", "brightness": 999, "id": 5})
    assert out[-1]["type"] == "error" and out[-1]["id"] == 5
    device.handle({"type": "unknown_future", "id": 6})
    assert out[-1]["type"] == "error"  # poprzednia wiadomość – nieznane typy bez odpowiedzi

    device.handle_line(b"{broken")
    assert out[-1] == {
        "type": "error",
        "msg": "invalid json: Expecting property name enclosed in double quotes",
    }

    clock.advance(3.5)  # brak ping → offline
    assert not device.online
    assert device.screen().kind == "offline"


def test_simulated_device_fallback_hid_when_offline() -> None:
    clock = ManualClock()
    device = SimulatedDevice(clock=clock)
    device.handle(
        protocol.msg_set_fallback(
            [protocol.FallbackBinding(1, mods=("ctrl",), code="c")], replace=False
        )
    )
    clock.advance(5)
    device.press(1)
    device.press(8)
    assert device.hid_log == [
        "1: {'mods': ['ctrl'], 'code': 'c'}",
        "8: {'media': 'mute'}",
    ]


def test_simulator_transport_end_to_end() -> None:
    device = SimulatedDevice()
    transport = SimulatorTransport(device)
    received: list[dict[str, Any]] = []
    transport.on_message = received.append
    transport.start()
    assert transport.connected
    assert transport.port_name == "symulator"
    device.press(2)
    assert received[-1] == {"type": "key", "key": 2, "action": "down", "t": received[-1]["t"]}
    assert transport.send(protocol.msg_flash("Hej", 1))
    assert device.screen().kind in ("flash", "splash")


def test_simulated_pro_micro_needs_split_fallback() -> None:
    out: list[dict[str, Any]] = []
    device = SimulatedDevice(board="promicro", emit=out.append)
    device.handle_line(protocol.encode(protocol.msg_hello("x")))
    assert out[-1]["board"] == "promicro" and out[-1]["max_line"] == 272

    bindings = [protocol.FallbackBinding(i, ("ctrl", "shift", "alt"), "f12") for i in range(1, 9)]
    device.handle_line(protocol.encode(protocol.msg_set_fallback(bindings)))
    assert out[-1] == {"type": "error", "msg": "line too long"}

    for i, message in enumerate(protocol.msgs_set_fallback(bindings, device.max_line)):
        device.handle_line(protocol.encode({**message, "id": i}))
        assert out[-1] == {"type": "ack", "id": i}
    assert set(device.fallback) == {str(i) for i in range(1, 9)}
