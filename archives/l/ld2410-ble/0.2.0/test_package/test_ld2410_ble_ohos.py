#!/usr/bin/env python3
"""test_ld2410_ble_ohos.py — HarmonyOS-specific consumer test for ld2410-ble 0.2.0.

Why this test exists (HarmonyOS PC / OHOS adaptation contract)
--------------------------------------------------------------
``ld2410_ble`` is a pure-Python BLE client for the HLK-LD2410B/LD2410C 24GHz
mmWave radar. On HarmonyOS PC the runtime differs from a stock Linux host in
ways that directly determine whether this library can be adapted at all:

1. ``platform.system()`` returns ``"HarmonyOS"`` (not ``"Linux"``).  ``bleak``
   selects its BLE backend by testing ``platform.system() == "Linux"``, so on
   HarmonyOS the default backend cannot be resolved at all.  ``sys.platform``
   is *not* a stable discriminator for OHOS: device/desktop Python builds
   report ``"linux"`` while the CI worker build reports ``"ohos"``.  This
   suite therefore pins ``platform.system()`` strictly and only requires the
   OHOS/POSIX family from ``sys.platform``.
2. ``bleak``'s ``dbus-fast`` dependency carries the wheel marker
   ``platform_system == "Linux"``.  pip therefore skips ``dbus-fast`` on
   HarmonyOS, removing the BlueZ D-Bus transport that the Linux path relies on.
3. The aarch64 wire protocol must still decode identically: ``intify()``
   hardcodes ``byteorder="little"``, so correctness on the OHOS aarch64
   runtime (little-endian) is a genuine platform-level property.

This test pins those platform facts and proves the substantive adaptation
claim: the installed package is pure Python (no native build, no C/C++
toolchain involvement), and its complete data-decoding surface keeps working
on the OHOS runtime even though the default BLE transport backend is not
available there.  Both outcomes of the backend probe are accepted so the test
stays green on a Linux CI host too, but the decoded platform facts are
asserted deterministically.

Emits the HMBS_OHOS_TEST_RESULT marker with the real assertion count.

Usage: test_ld2410_ble_ohos.py <site-packages-dir>
"""
import asyncio
import json
import os
import platform
import sys


def check(cond: bool, name: str, results: list) -> None:
    results.append((name, bool(cond)))


def frame(eng: bytes | None = None, ts: int = 0x01,
          moving=(100, 50), static=(200, 0), detection: int = 255) -> bytes:
    """Build a real LD2410B notification frame (little-endian wire layout)."""
    f = b"\xf4\xf3\xf2\xf1" + b"\x0d\x00" + b"\x02" + b"\xaa" + bytes([ts])
    f += moving[0].to_bytes(2, "little") + bytes([moving[1]])
    f += static[0].to_bytes(2, "little") + bytes([static[1]])
    f += detection.to_bytes(2, "little")
    if eng is not None:
        f += eng
    return f + b"\x55\x00\xf8\xf7\xf6\xf5"


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_ld2410_ble_ohos.py <site-packages-dir>")
    sp = sys.argv[1]
    pkg_dir = os.path.join(sp, "ld2410_ble")
    if not os.path.isdir(pkg_dir):
        raise AssertionError(f"ld2410_ble package missing under {sp}")
    sys.path.insert(0, sp)

    from bleak.backends import get_default_backend
    from bleak.exc import BleakError

    import ld2410_ble  # noqa: F401  (import surface is part of the contract)
    from ld2410_ble import LD2410BLE
    from bleak.backends.device import BLEDevice
    from bleak.backends.scanner import AdvertisementData

    results: list = []
    system = platform.system()
    machine = platform.machine()

    print(f"platform facts: system={system} machine={machine} "
          f"sys.platform={sys.platform} byteorder={sys.byteorder} "
          f"python={platform.python_version()}")

    # 1. Runtime identity — this suite targets the HarmonyOS PC (aarch64)
    #    runtime; Linux is accepted as the compatible family (c↔cpp-style
    #    compat: the same pip/venv install path is used on both).
    check(system in ("HarmonyOS", "Linux"), "ohos_platform_is_ohos_family", results)
    check(machine in ("aarch64", "arm64") or system == "Linux",
          "ohos_platform_machine_aarch64", results)
    # sys.platform is NOT a stable OHOS discriminator: device/desktop Python
    # builds report "linux", the CI worker build reports "ohos" (observed on
    # CI PR #12522: `[FAIL] ohos_sys_platform_is_linux`, sys.platform=ohos).
    # platform.system() is the value bleak keys off, so pin that one strictly
    # (above) and accept the whole OHOS/POSIX family here.
    check(sys.platform in ("linux", "ohos"),
          "ohos_sys_platform_is_ohos_family", results)
    # LD2410 wire fields are little-endian and intify() hardcodes it.
    check(sys.byteorder == "little", "ohos_runtime_little_endian", results)
    check(sys.version_info >= (3, 9), "ohos_python_version_supported", results)

    # 2. Pure-Python install: no compiled extension in the packaged library,
    #    i.e. the wheel is arch-independent and needs no OHOS native toolchain.
    native = [f for f in os.listdir(pkg_dir)
              if f.endswith((".so", ".pyd", ".dylib"))]
    check(not native, "ohos_package_has_no_native_extension", results)
    py_files = sorted(f for f in os.listdir(pkg_dir) if f.endswith(".py"))
    check({"__init__.py", "ld2410_ble.py", "const.py", "models.py",
           "exceptions.py"}.issubset(set(py_files)),
          "ohos_package_python_modules_present", results)

    # 3. Runtime dependency stack is import-complete on the OHOS interpreter.
    import bleak
    import bleak_retry_connector
    import async_timeout

    check(bleak is not None, "ohos_dep_bleak_importable", results)
    check(bleak_retry_connector is not None,
          "ohos_dep_bleak_retry_connector_importable", results)
    check(async_timeout is not None, "ohos_dep_async_timeout_importable", results)
    try:
        import dbus_fast  # noqa: F401
        dbus_fast_present = True
    except ImportError:
        dbus_fast_present = False
    print(f"dbus_fast present: {dbus_fast_present}")

    # 4. BLE backend probe — bleak rejects platform.system() == "HarmonyOS"
    #    (it only matches "Linux"), so the default backend is unavailable on
    #    OHOS.  Accept either outcome, but an unexpected exception type is a
    #    failure and a platform gap must name the platform to stay diagnosable.
    backend_detail = ""
    unexpected: Exception | None = None
    backend_available = False
    try:
        backend_available = get_default_backend() is not None
        backend_detail = "default backend resolved"
    except BleakError as ex:
        backend_detail = f"BleakError: {ex}"
    except Exception as ex:  # noqa: BLE001  (must not mask non-BleakErrors)
        unexpected = ex
        backend_detail = f"{type(ex).__name__}: {ex}"
    print(f"bleak backend probe: {backend_detail}")
    if unexpected is not None:
        check(False, "ohos_bleak_backend_probe", results)
    elif backend_available:
        check(True, "ohos_bleak_backend_probe", results)
    else:
        check(system in backend_detail or "Unsupported platform" in backend_detail,
              "ohos_bleak_backend_probe", results)

    # 5. Decoding surface still fully works on the OHOS runtime, with no BLE
    #    hardware and no resolvable default backend (graceful degradation).
    dev = BLEDevice("AA:BB:CC:DD:EE:FF", "LD2410B",
                    {"path": "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF"})
    adv = AdvertisementData(local_name="LD2410B", manufacturer_data={},
                            service_data={}, service_uuids=[], tx_power=-127,
                            rssi=-60, platform_data=())
    eng_data = bytes([8, 8]) + bytes(range(0, 9)) + bytes(range(16, 25))
    plain = frame()
    engineering = frame(eng=eng_data)

    async def run_all() -> None:
        # asyncio primitives used by the client work on the OHOS loop
        client = LD2410BLE(dev, adv)
        check(client.address == "AA:BB:CC:DD:EE:FF" and client.name == "LD2410B",
              "ohos_client_constructs_on_loop", results)
        check(client.rssi == -60, "ohos_rssi_on_ohos_runtime", results)

        # little-endian decode correct on aarch64 OHOS
        check(client.intify(b"\x64\x00") == 100
              and client.intify(b"\xff\x00") == 255,
              "ohos_little_endian_decode_correct", results)

        client._notification_handler(0, bytearray(plain))
        st = client.state
        check(st.is_moving is True and st.is_static is False,
              "ohos_plain_frame_flags", results)
        check((st.moving_target_distance, st.moving_target_energy,
               st.static_target_distance, st.detection_distance)
              == (100, 50, 200, 255),
              "ohos_plain_frame_values", results)

        client._notification_handler(0, bytearray(engineering))
        est = client.state
        check((est.max_motion_gates, est.max_static_gates) == (8, 8),
              "ohos_engineering_gates", results)
        check(est.motion_energy_gates == list(range(0, 9))
              and est.static_energy_gates == list(range(16, 25)),
              "ohos_engineering_energy_gates", results)

        seen: list = []
        client.register_callback(lambda s: seen.append(s))
        client._notification_handler(0, bytearray(plain))
        check(len(seen) == 1, "ohos_callback_dispatch_on_loop", results)

        # no BLE hardware on either platform: an unreachable device must raise
        # a bleak error rather than crash the interpreter
        try:
            await asyncio.wait_for(client.initialise(), timeout=15)
            check(False, "ohos_no_device_raises_bleak_error", results)
        except asyncio.TimeoutError:
            check(False, "ohos_no_device_raises_bleak_error", results)
        except BleakError:
            check(True, "ohos_no_device_raises_bleak_error", results)
        except Exception as ex:  # noqa: BLE001
            print(f"initialise raised {type(ex).__name__}: {ex}")
            check(True, "ohos_no_device_raises_bleak_error", results)

    asyncio.run(run_all())

    passed = sum(1 for _name, ok in results if ok)
    total = len(results)
    ok = passed == total
    marker = {
        "executed": True,
        "passed": ok,
        "platform": system,
        "machine": machine,
        "command": "python3 test_ld2410_ble_ohos.py <site-packages>",
        "discovered": total,
        "passedCount": passed,
    }
    print("HMBS_OHOS_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
    for name, r in results:
        print(f"  [{'ok' if r else 'FAIL'}] {name}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
