#!/usr/bin/env python3
"""Conan test_package for kegtron-ble — R34 consumer verification.

HARD: the `kegtron_ble` package files are present in site-packages and
importable; the parser is substantively exercised: parse a real Kegtron
KT-100 BLE advertisement (27-byte manufacturer data frame, same payload
shape as upstream tests/test_parser.py) and verify device identification
(KT-100 / Kegtron / single port), keg size & type decoding, volume
start/dispensed conversion, port state and port name — plus signal
strength passthrough.

Python-level runtime deps (sensor-state-data / bluetooth-data-tools /
bluetooth-sensor-state-data / home-assistant-bluetooth) are not on the
ohpcd conan registry; they are vendored here via pip wheels (the exact
versions pinned by upstream's poetry.lock) so the import graph resolves.
"""
import os
import subprocess
import sys

SMOKE_PY = r'''
import sys, os
sys.path[0:0] = [p for p in os.environ["KEGTRON_PYTHONPATH"].split(":") if p]

import kegtron_ble
from kegtron_ble import KegtronBluetoothDeviceData
print("kegtron_ble", kegtron_ble.__version__)

from home_assistant_bluetooth import BluetoothServiceInfo

# 真实解析：Kegtron KT-100 单口设备广告帧（27 字节 manufacturer data，
# 与上游 tests/test_parser.py 的 KT-100 载荷同形状）
parser = KegtronBluetoothDeviceData()
service_info = BluetoothServiceInfo(
    name="D0:CF:5E:5C:9B:75",
    manufacturer_data={
        65535: b"I\xef\x13\x88\x02\xe2\x01Single Port\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    },
    address="D0:CF:5E:5C:9B:75",
    rssi=-82,
    service_uuids=[],
    service_data={},
    source="local",
)
result = parser.update(service_info)

assert result is not None, "parser.update returned None"

# 设备识别：KT-100 单口设备
dev = result.devices[None]
assert dev.name == "Kegtron KT-100 9B75", dev.name
assert dev.model == "KT-100", dev.model
assert dev.manufacturer == "Kegtron", dev.manufacturer
assert result.title == "Kegtron KT-100 9B75", result.title

# 传感器值：keg_size 18.927L（Corny 5.0 gal 桶型）
values = result.entity_values
by_key = {k.key: v.native_value for k, v in values.items()}
keg_size = by_key.get("keg_size")
keg_type = by_key.get("keg_type")
vol_start = by_key.get("volume_start")
vol_disp = by_key.get("volume_dispensed")
port_state = by_key.get("port_state")
port_name = by_key.get("port_name")
port_count = by_key.get("port_count")
sig = by_key.get("signal_strength")

assert keg_size == 18.927, keg_size           # 18927 -> 18.927 L
assert keg_type == "Corny (5.0 gal)", keg_type
assert vol_start == 5.0, vol_start             # 5000 -> 5.0 L
assert vol_disp == 0.738, vol_disp             # 738 -> 0.738 L
assert port_state == "Configured", port_state
assert port_name == "Single Port", port_name
assert port_count == "Single port device", port_count
assert sig == -82, sig

# entity_descriptions 完整性：8 个传感器描述已注册
assert len(result.entity_descriptions) == 8, len(result.entity_descriptions)

print("OK: KT-100 parse (device id + keg size/type + volumes + port state)")
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    lib_root = os.path.join(pkg, "lib")
    site = None
    for py in os.listdir(lib_root):
        cand = os.path.join(lib_root, py, "site-packages")
        if os.path.isdir(cand) and os.path.isdir(
                os.path.join(cand, "kegtron_ble")):
            site = cand
            break
    if not site:
        print(f"FAIL: kegtron_ble module not found under {lib_root}",
              file=sys.stderr)
        return 1

    # 1. HARD: 包核心文件存在
    mod_dir = os.path.join(site, "kegtron_ble")
    required = ["__init__.py", "parser.py", "py.typed"]
    missing = [f for f in required
               if not os.path.isfile(os.path.join(mod_dir, f))]
    if missing:
        print(f"FAIL: missing files {missing} in {mod_dir}",
              file=sys.stderr)
        return 1

    # 2. Python 级运行时依赖（上游 poetry.lock 锁定组合）——未在 ohpcd
    #    conan 仓发布，从 OHOS pypi 镜像 vendor 到 $TMPDIR 组 PYTHONPATH
    #    （不写 test_package 源码目录——conan create 复跑不残留）
    import tempfile
    vendor = os.path.join(
        tempfile.gettempdir(), "kegtron-ble-test-pydeps")
    deps_ok = _vendor_deps(vendor)
    py_path = [site] + ([vendor] if deps_ok else [])

    # 3. 真实解析验证（子进程隔离——避免本进程 sys.path 污染；
    #    smoke 脚本同样写到 $TMPDIR）
    script = os.path.join(
        tempfile.gettempdir(), "kegtron-ble-smoke-test.py")
    with open(script, "w") as f:
        f.write(SMOKE_PY)
    env = dict(os.environ)
    env["KEGTRON_PYTHONPATH"] = os.pathsep.join(py_path)
    r = subprocess.run([sys.executable, script], env=env,
                       capture_output=True, text=True, timeout=600)
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        print("FAIL: smoke parse test", file=sys.stderr)
        return 1
    print("PASS: kegtron-ble consumer verification (R34)")
    return 0


def _vendor_deps(vendor):
    """pip 下载上游 lock 锁定的 4 个纯 Python 依赖 wheel 并解压
    （复用条件：sensor_state_data 目录已解压即视为完成）。"""
    if os.path.isdir(os.path.join(vendor, "sensor_state_data")):
        return True
    try:
        import zipfile
        wheels = [
            ("sensor_state_data-2.19.0-py3-none-any.whl",
             "https://pypi.repo.openharmony.cn/artifactory/openharmony-pypi/"
             "packages/ce/63/e140aaec77bdc1f7b949e40712fc2f932023d9ad5cf211bb"
             "de969f516a55/sensor_state_data-2.19.0-py3-none-any.whl"),
            ("bluetooth_data_tools-0.3.1-py3-none-any.whl",
             "https://pypi.repo.openharmony.cn/artifactory/openharmony-pypi/"
             "packages/e6/9b/e53fc7eb05f059dcd9b3b1e4a78ce2f9a796f49edf8ec74e"
             "d1326d31017b/bluetooth_data_tools-0.3.1-py3-none-any.whl"),
            ("bluetooth_sensor_state_data-1.7.5-py3-none-any.whl",
             "https://pypi.repo.openharmony.cn/artifactory/openharmony-pypi/"
             "packages/64/52/287844cf648235f2baf734dbfd0b5657c61b547c014010b78"
             "b579312a8a3/bluetooth_sensor_state_data-1.7.5-py3-none-any.whl"),
            ("home_assistant_bluetooth-1.4.0-py3-none-any.whl",
             "https://pypi.repo.openharmony.cn/artifactory/openharmony-pypi/"
             "packages/19/42/6804e6b6037fd0c852303d534ef58ca29846f9cdc51a2a39"
             "1bd972101b7b/home_assistant_bluetooth-1.4.0-py3-none-any.whl"),
        ]
        os.makedirs(vendor, exist_ok=True)
        import urllib.request
        for fname, url in wheels:
            out = os.path.join(vendor, fname)
            if not os.path.exists(out):
                req = urllib.request.Request(
                    url, headers={"User-Agent": "atomcode"})
                with urllib.request.urlopen(req, timeout=300) as resp:
                    data = resp.read()
                with open(out, "wb") as f:
                    f.write(data)
            with zipfile.ZipFile(out) as z:
                z.extractall(vendor)
        return True
    except Exception as e:
        print(f"WARN: vendor deps failed: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    sys.exit(main())
