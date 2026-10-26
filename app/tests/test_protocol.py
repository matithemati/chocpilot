from __future__ import annotations

import pytest

from chocpilot.core import protocol
from chocpilot.core.protocol import (
    DeviceInfo,
    EncoderEvent,
    ErrorEvent,
    FallbackBinding,
    KeyEvent,
    ProtocolError,
)


def test_encode_decode_roundtrip() -> None:
    msg = protocol.msg_flash("Spotify", key=3, ms=1200)
    data = protocol.encode(msg)
    assert data.endswith(b"\n")
    assert protocol.decode(data) == {"type": "flash", "text": "Spotify", "ms": 1200, "key": 3}


@pytest.mark.parametrize("line", [b"", b"{oops", b"[1,2]", b'{"x":1}', b"\xff\xfe"])
def test_decode_rejects_invalid(line: bytes) -> None:
    with pytest.raises(ProtocolError):
        protocol.decode(line)


def test_encode_too_long() -> None:
    with pytest.raises(ProtocolError):
        protocol.encode({"type": "x", "data": "a" * 2000})


def test_transliteration() -> None:
    assert protocol.transliterate("Zażółć gęślą jaźń") == "Zazolc gesla jazn"
    assert protocol.transliterate("Głośność…") == "Glosnosc..."
    assert protocol.fit("Przeglądarka", 7) == "Przegla"


def test_display_grid_pads_and_truncates() -> None:
    msg = protocol.msg_display_grid("Domyślny", ["Kalkulator", "Łódź"])
    assert msg["title"] == "Domyslny"
    assert msg["labels"][:2] == ["Kalkula", "Lodz"]
    assert len(msg["labels"]) == 9
    assert msg["labels"][8] == ""


def test_display_bar_clamps() -> None:
    assert protocol.msg_display_bar("Vol", 150)["value"] == 100
    assert protocol.msg_display_bar("Vol", -3)["value"] == 0
    assert protocol.msg_display_bar("Vol", 42.6, ms=0) == {
        "type": "display",
        "mode": "bar",
        "title": "Vol",
        "value": 43,
    }


def test_settings_validation() -> None:
    assert protocol.msg_settings(brightness=10, flip=True) == {
        "type": "settings",
        "brightness": 10,
        "flip": True,
    }
    with pytest.raises(ProtocolError):
        protocol.msg_settings(brightness=300)
    with pytest.raises(ProtocolError):
        protocol.msg_settings(flip=1)
    with pytest.raises(ProtocolError):
        protocol.msg_settings(enc_pulses=True)
    with pytest.raises(ProtocolError):
        protocol.msg_settings(color="red")


def test_set_fallback_message() -> None:
    msg = protocol.msg_set_fallback(
        [
            FallbackBinding(1, mods=("ctrl", "shift"), code="c"),
            FallbackBinding("enc_cw", media="vol_up"),
            FallbackBinding(5),
        ]
    )
    assert msg == {
        "type": "set_fallback",
        "replace": True,
        "bindings": [
            {"key": 1, "mods": ["ctrl", "shift"], "code": "c"},
            {"key": "enc_cw", "media": "vol_up"},
            {"key": 5},
        ],
    }


def test_parse_device_messages() -> None:
    info = protocol.parse_device_message(
        {"type": "hello", "device": "chocpilot", "fw": "1.0.0", "board": "xiao_esp32s3", "keys": 10}
    )
    assert isinstance(info, DeviceInfo)
    assert info.board_name == "XIAO ESP32-S3"
    assert protocol.parse_device_message(
        {"type": "key", "key": 10, "action": "up", "t": 5}
    ) == KeyEvent(10, False, 5)
    assert protocol.parse_device_message({"type": "enc", "steps": -3, "t": 9}) == EncoderEvent(
        -3, 9
    )
    assert protocol.parse_device_message({"type": "error", "msg": "invalid json"}) == ErrorEvent(
        None, "invalid json"
    )
    assert protocol.parse_device_message({"type": "brand_new", "x": 1}) is None


@pytest.mark.parametrize(
    "msg",
    [
        {"type": "hello", "device": "other"},
        {"type": "key", "key": 11, "action": "down"},
        {"type": "key", "key": 1, "action": "pressed"},
        {"type": "enc", "steps": "2"},
        {"type": "key", "key": True, "action": "down"},
    ],
)
def test_parse_device_message_invalid(msg: dict) -> None:
    with pytest.raises(ProtocolError):
        protocol.parse_device_message(msg)


def test_hello_display_diagnostics() -> None:
    base = {"type": "hello", "device": "chocpilot", "fw": "1.0.1", "board": "kb2040"}
    old = protocol.parse_device_message(base)
    assert isinstance(old, DeviceInfo) and not old.has_diag and old.oled_status == "?"
    found = protocol.parse_device_message({**base, "oled": 0x3D, "i2c": [0x3D, 0x50]})
    assert isinstance(found, DeviceInfo)
    assert found.oled_addr == 0x3D and found.i2c_devices == (0x3D, 0x50)
    assert found.oled_status == "0x3D"
    missing = protocol.parse_device_message({**base, "oled": None, "i2c": []})
    assert isinstance(missing, DeviceInfo)
    assert missing.has_diag and missing.oled_addr is None and missing.oled_status == "brak"


def test_hello_line_levels_and_swap() -> None:
    info = protocol.parse_device_message(
        {
            "type": "hello",
            "device": "chocpilot",
            "fw": "1.0.3",
            "board": "kb2040",
            "oled": None,
            "i2c": [],
            "lines": {"sda": 0, "scl": 1},
            "swapped": True,
        }
    )
    assert isinstance(info, DeviceInfo)
    assert info.sda_level == 0 and info.scl_level == 1 and info.swapped


def test_hello_pro_micro_max_line() -> None:
    base = {"type": "hello", "device": "chocpilot", "fw": "1.0.4", "board": "promicro"}
    info = protocol.parse_device_message({**base, "max_line": 272})
    assert isinstance(info, DeviceInfo)
    assert info.board_name == "Pro Micro" and info.max_line == 272
    for bad in ("272", True, None):
        other = protocol.parse_device_message({**base, "max_line": bad})
        assert isinstance(other, DeviceInfo) and other.max_line == protocol.MAX_LINE_LENGTH
    tiny = protocol.parse_device_message({**base, "max_line": 10})
    assert isinstance(tiny, DeviceInfo) and tiny.max_line == protocol.MIN_LINE_LENGTH


def test_set_fallback_split_for_small_devices() -> None:
    bindings = [FallbackBinding(i, ("ctrl", "shift", "alt"), "f12") for i in range(1, 11)]
    bindings += [
        FallbackBinding("enc_cw", media="vol_up"),
        FallbackBinding("enc_ccw", media="mute"),
    ]
    whole = protocol.msgs_set_fallback(bindings)
    assert whole == [protocol.msg_set_fallback(bindings, replace=True)]

    parts = protocol.msgs_set_fallback(bindings, 272)
    assert len(parts) > 1
    assert parts[0]["replace"] is True
    assert all(p["replace"] is False for p in parts[1:])
    assert [b for p in parts for b in p["bindings"]] == whole[0]["bindings"]
    for part in parts:
        assert len(protocol.encode({**part, "id": 2**31 - 1})) <= 272

    assert protocol.msgs_set_fallback([], 272) == [protocol.msg_set_fallback([], replace=True)]
