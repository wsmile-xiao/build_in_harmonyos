#!/usr/bin/env python3
"""test_rapt_ble.py — consumer test source for rapt-ble 0.1.2 (L0c).

REAL API check (R34): exercises the packaged library's public API with the
same hex payloads used by the upstream test suite (tests/test_parser.py) — no
BLE hardware needed, pure payload decoding. The decoded metrics are
additionally cross-validated against an independent struct.unpack() of the
same payload, so a wrong constant inside the parser cannot pass unnoticed.

Covered:
  * rapt_ble.__version__ / __all__ exports
  * RAPTPillBluetoothDeviceData.supported() for the v1 and v2 payloads
  * update() -> SensorUpdate entity values (specific gravity / temperature /
    battery / signal strength) for the v1 payload
  * device identity (name / manufacturer / model / title)
  * the "KEG..." version advertisement -> sw_version
  * the "PTdPillG1" hardware-revision advertisement and wrong-length payloads
    are ignored without raising
Emits the HMBS_TEST_PACKAGE_RESULT marker with the real assertion count.
Usage: test_rapt_ble.py <site-packages-dir>
"""
import json
import os
import struct
import sys

# Upstream payloads (tests/test_parser.py)
PAYLOAD_V1 = b"RAPT\x01x\xe3m<\xb9\x94\x94\x8bD|\xb9\xf64E\x02b&w*\xac"
PAYLOAD_V2_NO_GV = b"RAPT\x02\x00\x00\x00\x00\x00\x00\x94\x8bD|\xb9\xf64E\x02b&w*\xac"
PAYLOAD_V2_GV = b"RAPT\x02\x00\x01\x3e\x9d\xd1\xab\x94\x8bD|\xb9\xf64E\x02b&w*\xac"
PAYLOAD_VERSION = b"KEG20220612_050156_81c6d1"
PAYLOAD_HW_REV = b"RAPTdPillG1"


def check(cond: bool, name: str, results: list) -> None:
    results.append((name, bool(cond)))


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_rapt_ble.py <site-packages-dir>")
    sp = sys.argv[1]
    if not os.path.isdir(os.path.join(sp, "rapt_ble")):
        raise AssertionError(f"rapt_ble package missing under {sp}")
    sys.path.insert(0, sp)

    results: list = []

    # 0. Distribution metadata is really the packaged one.
    import rapt_ble
    from rapt_ble import RAPTPillBluetoothDeviceData
    from rapt_ble.parser import RAPTPillBluetoothDeviceData as ParserClass

    check(rapt_ble.__version__ == "0.1.2", "module_version", results)
    check(RAPTPillBluetoothDeviceData is ParserClass, "public_export_identity", results)
    check(
        set(rapt_ble.__all__)
        == {
            "DeviceClass",
            "DeviceKey",
            "SensorUpdate",
            "RAPTPillBluetoothDeviceData",
            "Units",
        },
        "public_export_list",
        results,
    )

    # 1. supported() — same three payloads as upstream test_device_supported.
    for tag, payload in (
        ("v1", PAYLOAD_V1),
        ("v2_no_gravity_velocity", PAYLOAD_V2_NO_GV),
        ("v2_gravity_velocity", PAYLOAD_V2_GV),
    ):
        device = RAPTPillBluetoothDeviceData()
        check(device.supported(service_info(payload)), f"supported_{tag}", results)

    # 2. Version advertisement -> sw_version (upstream test_parse_version).
    version_device = RAPTPillBluetoothDeviceData()
    version_device.update(service_info(PAYLOAD_VERSION))
    check(
        version_device._get_device_info(None).sw_version == "20220612_050156_81c6d1",
        "parse_sw_version",
        results,
    )

    # 3. Metrics decoding (upstream test_parse_metrics) for the v1 payload,
    #    cross-validated against an independent struct.unpack of the payload.
    #    Payload layout (>B6sHfhhhh on payload[4:], i.e. after the "RAPT"):
    #      version, mac, temperature (x/128-273.15), gravity (/1000),
    #      x/y/z (/16), battery (x/256)
    (
        _version,
        mac,
        raw_temperature,
        raw_gravity,
        raw_x,
        raw_y,
        raw_z,
        raw_battery,
    ) = struct.unpack(">B6sHfhhhh", PAYLOAD_V1[4:])
    expected_gravity = round(raw_gravity / 1000, 4)
    expected_temperature = round(raw_temperature / 128 - 273.15, 2)
    expected_battery = round(raw_battery / 256)
    check(_version == 1, "payload_layout_version", results)
    check(mac.hex() == "78e36d3cb994", "payload_layout_mac", results)
    check((raw_x, raw_y, raw_z) == (13381, 610, 9847), "payload_layout_acceleration", results)

    from sensor_state_data import DeviceKey

    device = RAPTPillBluetoothDeviceData()
    update = device.update(service_info(PAYLOAD_V1))

    check(update.title == "RAPT Pill 4455", "metrics_title", results)
    info = update.devices[None]
    check(info.name == "RAPT Pill 4455", "metrics_device_name", results)
    check(info.manufacturer == "RAPT", "metrics_manufacturer", results)
    check(info.model == "RAPT Pill hydrometer", "metrics_model", results)
    check(info.sw_version is None, "metrics_sw_version_none", results)

    values = {key.key: value.native_value for key, value in update.entity_values.items()}
    check(set(values) == {"specific_gravity", "temperature", "battery", "signal_strength"},
          "metrics_keys", results)
    check(values["specific_gravity"] == 1.0109, "metrics_specific_gravity_literal", results)
    check(values["specific_gravity"] == expected_gravity,
          "metrics_specific_gravity_struct", results)
    check(values["temperature"] == 23.94, "metrics_temperature_literal", results)
    check(values["temperature"] == expected_temperature, "metrics_temperature_struct", results)
    check(values["battery"] == 43, "metrics_battery_literal", results)
    check(values["battery"] == expected_battery, "metrics_battery_struct", results)
    check(values["signal_strength"] == -60, "metrics_signal_strength", results)
    check(
        update.entity_values[DeviceKey(key="specific_gravity", device_id=None)].name
        == "Specific Gravity",
        "metrics_specific_gravity_name",
        results,
    )

    # 4. Non-metric advertisements must be ignored gracefully: only the RSSI
    #    derived signal_strength may show up, no hydrometer metrics at all.
    def metric_keys(update) -> set:
        return {key.key for key in update.entity_values}

    hw_rev = RAPTPillBluetoothDeviceData().update(service_info(PAYLOAD_HW_REV))
    check(metric_keys(hw_rev) == {"signal_strength"},
          "hw_revision_advertisement_ignored", results)

    short = RAPTPillBluetoothDeviceData().update(service_info(b"RAPT\x01short"))
    check(metric_keys(short) == {"signal_strength"}, "short_payload_ignored", results)

    unknown = RAPTPillBluetoothDeviceData().update(service_info(b"XXXX\x01" + b"\x00" * 21))
    check(unknown.entity_values == {}, "unknown_manufacturer_ignored", results)

    passed = sum(1 for _name, ok in results if ok)
    total = len(results)
    ok = passed == total
    marker = {
        "executed": True,
        "passed": ok,
        "command": "python3 test_rapt_ble.py <site-packages>",
        "discovered": total,
        "passedCount": passed,
    }
    print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
    for name, r in results:
        print(f"  [{'ok' if r else 'FAIL'}] {name}")
    return 0 if ok else 1


def service_info(payload: bytes):
    """Same helper as upstream tests/test_parser.py:bytes_to_service_info."""
    from home_assistant_bluetooth import BluetoothServiceInfo

    manufacturer_data = {}
    (manufacturer_id,) = struct.unpack("<H", payload[:2])
    manufacturer_data[manufacturer_id] = payload[2:]
    return BluetoothServiceInfo(
        name="",
        address="00:11:22:33:44:55",
        rssi=-60,
        manufacturer_data=manufacturer_data,
        service_data={},
        service_uuids=[],
        source="local",
    )


if __name__ == "__main__":
    sys.exit(main())
