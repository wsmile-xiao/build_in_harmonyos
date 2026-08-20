#!/usr/bin/env python3
"""test_airthings_ble.py — consumer test source for airthings-ble 1.2.0 (L0c).

REAL API check (R34): exercises the packaged library's public API with the
same hex payloads used by the upstream test suite (tests/test_wave_mini.py
etc.) — no BLE hardware needed, pure decoding logic:
  * AirthingsDeviceType enum (device model ids -> product names)
  * sensor_decoders._decode_wave_plus / _decode_wave_radon (hex payload decode)
  * radon_level.get_radon_level (radon level classification)
  * atom.request.AtomRequest (ATOM request serialization)
Emits the HMBS_TEST_PACKAGE_RESULT marker with the real assertion count.
Usage: test_airthings_ble.py <site-packages-dir>
"""
import json
import os
import sys


def check(cond: bool, name: str, results: list) -> None:
    results.append((name, bool(cond)))


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_airthings_ble.py <site-packages-dir>")
    sp = sys.argv[1]
    if not os.path.isdir(os.path.join(sp, "airthings_ble")):
        raise AssertionError(f"airthings_ble package missing under {sp}")
    sys.path.insert(0, sp)

    results: list = []

    # 1. Device type enum mapping (upstream tests/test_device_type.py data)
    from airthings_ble.device_type import AirthingsDeviceType

    check(AirthingsDeviceType.WAVE_MINI.product_name == "Wave Mini", "device_type_wave_mini", results)
    check(AirthingsDeviceType.WAVE_PLUS.product_name == "Wave Plus", "device_type_wave_plus", results)
    check(AirthingsDeviceType.WAVE_RADON.product_name == "Wave Radon", "device_type_wave_radon", results)
    check(AirthingsDeviceType("2920") == AirthingsDeviceType.WAVE_MINI, "device_type_raw_2920", results)

    # 2. Wave Plus sensor decoding (upstream tests/test_wave_plus.py payload,
    #    identical to test_wave_mini.py's test_wave_plus_sensor_data).
    # Decoder mapping (upstream airthings_ble/sensor_decoders.py,
    #    _decode_wave_plus): "<4B8H" unpacks to (b0..b3, h0..h7). Values are:
    #    humidity=val[1]/2.0  -> 0x38=56   -> 28.0
    #    radon_1day_avg=val[4]            -> 11
    #    radon_longterm_avg=val[5]        -> 34
    #    temperature=val[6]/100           -> 2493/100 = 24.93
    # All assertions below follow that formula; verified with struct.unpack.
    from airthings_ble.sensor_decoders import _decode_wave_plus

    raw = bytearray.fromhex("01380d800b002200bd094cc31d036c0000007d05")
    decoded = _decode_wave_plus(name="Plus", format_type="<4B8H", scale=1.0)(raw)
    check(decoded["humidity"] == 28.0, "decode_wave_plus_humidity", results)
    check(decoded["radon_1day_avg"] == 11, "decode_wave_plus_radon_1day", results)
    check(decoded["radon_longterm_avg"] == 34, "decode_wave_plus_radon_long", results)
    check(abs(decoded["temperature"] - 24.93) < 1e-6, "decode_wave_plus_temperature", results)

    # 3. Radon level classification (upstream tests/test_radon_level.py)
    from airthings_ble.radon_level import get_radon_level

    check(get_radon_level(0) == "good", "radon_level_good", results)
    check(get_radon_level(120) == "fair", "radon_level_fair", results)
    check(get_radon_level(300) == "poor", "radon_level_poor", results)

    # 4. ATOM request serialization (upstream tests/test_atom_request.py)
    from airthings_ble.atom.request import AtomRequest
    from airthings_ble.atom.request_path import AtomRequestPath

    req = AtomRequest(AtomRequestPath.LATEST_VALUES, random_bytes=bytes.fromhex("E473"))
    req_bytes = req.as_bytes()
    check(req_bytes[0:2] == bytes.fromhex("0301"), "atom_request_header", results)
    check(req_bytes[2:4] == bytes.fromhex("E473"), "atom_request_random", results)
    check(req_bytes[8:] == req.url.as_bytes(), "atom_request_url", results)

    # 5. Public parser entry point importable (upstream tests/test_corentium_home_2.py)
    from airthings_ble import AirthingsBluetoothDeviceData, AirthingsDeviceType as _DT  # noqa: F401
    check(AirthingsBluetoothDeviceData is not None, "parser_entry_import", results)

    passed = sum(1 for _name, ok in results if ok)
    total = len(results)
    ok = passed == total
    marker = {
        "executed": True,
        "passed": ok,
        "command": "python3 test_airthings_ble.py <site-packages>",
        "discovered": total,
        "passedCount": passed,
    }
    print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
    for name, r in results:
        print(f"  [{'ok' if r else 'FAIL'}] {name}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
