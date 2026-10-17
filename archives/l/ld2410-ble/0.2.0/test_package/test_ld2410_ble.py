#!/usr/bin/env python3
"""test_ld2410_ble.py — consumer test source for ld2410-ble 0.2.0 (L0c).

REAL API check (R34): exercises the packaged library's public API against the
LD2410B/LD2410C 24GHz mmWave presence-radar BLE wire protocol, using the same
frame layout the upstream suite (tests/test_init.py) targets. No BLE hardware
is required: every assertion runs through the pure-Python frame parser
(``LD2410BLE._notification_handler``) and the public state / property surface.

``LD2410BLE`` requires a running event loop (it snapshots
``asyncio.get_running_loop()`` in ``__init__``), so all checks execute inside
``asyncio.run()``.

Emits the HMBS_TEST_PACKAGE_RESULT marker with the real assertion count.

Usage: test_ld2410_ble.py <site-packages-dir>
"""
import asyncio
import json
import os
import sys


def check(cond: bool, name: str, results: list) -> None:
    results.append((name, bool(cond)))


def frame(eng: bytes | None = None, ts: int = 0x01,
          moving=(100, 50), static=(200, 0), detection: int = 255) -> bytes:
    """Build a real LD2410B notification frame (little-endian wire layout).

    Layout: F4F3F2F1 | length | engineering-mode | AA | target-state |
            moving-dist(2) moving-energy(1) static-dist(2) static-energy(1)
            detection-dist(2) | [engineering-data] | 55 00 F8F7F6F5
    """
    f = b"\xf4\xf3\xf2\xf1" + b"\x0d\x00" + b"\x02" + b"\xaa" + bytes([ts])
    f += moving[0].to_bytes(2, "little") + bytes([moving[1]])
    f += static[0].to_bytes(2, "little") + bytes([static[1]])
    f += detection.to_bytes(2, "little")
    if eng is not None:
        f += eng
    return f + b"\x55\x00\xf8\xf7\xf6\xf5"


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_ld2410_ble.py <site-packages-dir>")
    sp = sys.argv[1]
    if not os.path.isdir(os.path.join(sp, "ld2410_ble")):
        raise AssertionError(f"ld2410_ble package missing under {sp}")
    sys.path.insert(0, sp)

    import ld2410_ble
    from ld2410_ble import LD2410BLE, LD2410BLEState
    from ld2410_ble.const import (
        CHARACTERISTIC_NOTIFY,
        CHARACTERISTIC_WRITE,
        CMD_BT_PASS_DEFAULT,
        CMD_ENABLE_CONFIG,
        CMD_ENABLE_ENGINEERING_MODE,
    )

    from bleak.backends.device import BLEDevice
    from bleak.backends.scanner import AdvertisementData

    results: list = []

    # 1. Package import surface
    check(ld2410_ble is not None, "import_package", results)
    check(isinstance(ld2410_ble.__version__, str) and ld2410_ble.__version__,
          "version_metadata", results)

    # 2. Command / characteristic constants (wire contract)
    check(CHARACTERISTIC_NOTIFY == "0000fff1-0000-1000-8000-00805f9b34fb",
          "characteristic_notify_uuid", results)
    check(CHARACTERISTIC_WRITE == "0000fff2-0000-1000-8000-00805f9b34fb",
          "characteristic_write_uuid", results)
    check(CMD_BT_PASS_DEFAULT == b"HiLink", "bt_password_default", results)
    check(CMD_ENABLE_CONFIG == b"\xfd\xfc\xfb\xfa\x04\x00\xff\x00\x01\x00\x04\x03\x02\x01",
          "cmd_enable_config", results)
    check(CMD_ENABLE_ENGINEERING_MODE
          == b"\xfd\xfc\xfb\xfa\x02\x00b\x00\x04\x03\x02\x01",
          "cmd_enable_engineering_mode", results)

    # 3. State container defaults (frozen dataclass)
    default = LD2410BLEState()
    check(default.is_moving is False and default.is_static is False,
          "state_defaults_flags", results)
    check(default.max_motion_gates == 8 and default.max_static_gates == 8,
          "state_defaults_gates", results)
    check(default.motion_energy_gates == [0] * 9
          and default.static_energy_gates == [0] * 9,
          "state_defaults_energy_gates", results)
    try:
        default.is_moving = True  # type: ignore[misc]
        frozen_ok = False
    except Exception:
        frozen_ok = True
    check(frozen_ok, "state_dataclass_frozen", results)

    # 4. Device identity / advertisement surface
    dev = BLEDevice("AA:BB:CC:DD:EE:FF", "LD2410B",
                    {"path": "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF"})
    adv = AdvertisementData(local_name="LD2410B", manufacturer_data={},
                            service_data={}, service_uuids=[], tx_power=-127,
                            rssi=-60, platform_data=())

    eng_data = bytes([8, 8]) + bytes(range(0, 9)) + bytes(range(16, 25))
    plain = frame()
    engineering = frame(eng=eng_data)

    async def run_all() -> None:
        # identity + rssi
        client = LD2410BLE(dev, adv)
        check(client.address == "AA:BB:CC:DD:EE:FF", "device_address", results)
        check(client.name == "LD2410B", "device_name", results)
        check(client.rssi == -60, "rssi_from_advertisement", results)

        no_adv = LD2410BLE(dev)
        check(no_adv.rssi is None, "rssi_without_advertisement", results)

        # plain frame decoding
        client._notification_handler(0, bytearray(plain))
        st = client.state
        check(st.is_moving is True, "plain_frame_moving_flag", results)
        check(st.is_static is False, "plain_frame_static_flag", results)
        check((st.moving_target_distance, st.moving_target_energy) == (100, 50),
              "plain_frame_moving_distance_energy", results)
        check((st.static_target_distance, st.static_target_energy) == (200, 0),
              "plain_frame_static_distance_energy", results)
        check(st.detection_distance == 255, "plain_frame_detection_distance", results)
        check(client.is_moving is True, "is_moving_property", results)
        check(client.moving_target_distance == 100,
              "moving_target_distance_property", results)
        check(st.max_motion_gates is None and st.max_static_gates is None,
              "plain_frame_no_engineering_gates", results)

        # target-state bit flags: MOVING=1, STATIC=2
        def flags(ts: int):
            c = LD2410BLE(dev, adv)
            c._notification_handler(0, bytearray(frame(ts=ts)))
            return c.is_moving, c.is_static

        check(flags(0x00) == (False, False), "target_state_idle", results)
        check(flags(0x02) == (False, True), "target_state_static_only", results)
        check(flags(0x03) == (True, True), "target_state_both", results)

        # engineering frame decoding
        client._notification_handler(0, bytearray(engineering))
        est = client.state
        check((est.max_motion_gates, est.max_static_gates) == (8, 8),
              "engineering_frame_max_gates", results)
        check(est.motion_energy_gates == list(range(0, 9)),
              "engineering_frame_motion_energy_gates", results)
        check(est.static_energy_gates == list(range(16, 25)),
              "engineering_frame_static_energy_gates", results)
        check(client.motion_energy_gate_0 == 0 and client.motion_energy_gate_8 == 8,
              "motion_energy_gate_accessors", results)
        check(client.static_energy_gate_0 == 16 and client.static_energy_gate_8 == 24,
              "static_energy_gate_accessors", results)
        check(client.max_motion_gates == 8 and client.max_static_gates == 8,
              "max_gates_properties", results)
        check(len(client.motion_energy_gates) == 9
              and len(client.static_energy_gates) == 9,
              "energy_gate_list_length", results)

        # little-endian int conversion (wire byte order)
        check(client.intify(b"\x64\x00") == 100, "intify_little_endian", results)
        check(client.intify(b"\x00\x01") == 256, "intify_high_byte", results)

        # callbacks fire on each decoded notification; unregister works
        c2 = LD2410BLE(dev, adv)
        seen: list = []
        unregister = c2.register_callback(lambda s: seen.append(s))
        c2._notification_handler(0, bytearray(plain))
        c2._notification_handler(0, bytearray(plain))
        check(len(seen) == 2, "callback_fires_per_notification", results)
        check(len(c2._callbacks) == 1, "callback_registered", results)
        unregister()
        check(not c2._callbacks, "callback_unregister", results)

        disc: list = []
        c3 = LD2410BLE(dev, adv)
        unreg_disc = c3.register_disconnected_callback(lambda: disc.append(1))
        check(len(c3._disconnected_callbacks) == 1,
              "disconnected_callback_register", results)
        unreg_disc()
        check(not c3._disconnected_callbacks,
              "disconnected_callback_unregister", results)

        # a frame split across two notifications is buffered and decoded once
        c4 = LD2410BLE(dev, adv)
        c4._notification_handler(0, bytearray(plain[:7]))
        check(len(c4._buf) == 7 and c4.is_moving is False,
              "split_frame_buffered", results)
        c4._notification_handler(0, bytearray(plain[7:]))
        check(c4.is_moving is True and not c4._buf,
              "split_frame_completed", results)

        # stop() with no active client is a safe no-op
        try:
            await client.stop()
            stop_ok = client._client is None
        except Exception:
            stop_ok = False
        check(stop_ok, "stop_without_client_safe", results)

    asyncio.run(run_all())

    passed = sum(1 for _name, ok in results if ok)
    total = len(results)
    ok = passed == total
    marker = {
        "executed": True,
        "passed": ok,
        "command": "python3 test_ld2410_ble.py <site-packages>",
        "discovered": total,
        "passedCount": passed,
    }
    print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
    for name, r in results:
        print(f"  [{'ok' if r else 'FAIL'}] {name}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
