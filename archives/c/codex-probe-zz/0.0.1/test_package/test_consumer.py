#!/usr/bin/env python3
"""Consumer test for codex-probe-zz under OHOS.

Verifies:
  1. provider_probe module import
  2. codex_probe CLI --help
  3. packaged baseline data files are reachable
  4. list-baselines subcommand works locally
  5. OHOS platform fingerprint
"""
import os
import platform
import subprocess
import sys


def main(lib_dir: str) -> int:
    sys.path.insert(0, lib_dir)
    failures = []

    # 1. module import
    try:
        import provider_probe  # noqa: F401
        print("PASS: provider_probe import")
    except Exception as e:
        failures.append(f"provider_probe import failed: {e}")

    # 2. CLI --help
    entry = os.path.join(lib_dir, "codex_probe.py")
    r = subprocess.run([sys.executable, entry, "--help"],
                       capture_output=True, text=True)
    if r.returncode == 0 and "baseline" in r.stdout:
        print("PASS: codex_probe.py --help")
    else:
        failures.append(f"--help failed: rc={r.returncode}")

    # 3. baseline data files
    try:
        import codex_probe_data
        bdir = os.path.join(os.path.dirname(codex_probe_data.__file__), "baselines")
        js = [f for f in os.listdir(bdir) if f.endswith(".json")]
        assert js, "no baseline JSON"
        print(f"PASS: baselines found: {len(js)}")
    except Exception as e:
        failures.append(f"baseline data check failed: {e}")

    # 4. list-baselines
    r = subprocess.run([sys.executable, entry, "list-baselines"],
                       capture_output=True, text=True)
    if r.returncode == 0 and "baseline" in r.stdout.lower():
        print("PASS: list-baselines")
    else:
        failures.append(f"list-baselines failed: rc={r.returncode}")

    # 5. platform fingerprint (asserted)
    sysname = platform.system()
    machine = platform.machine()
    pyver = sys.version.split()[0]
    print(f"INFO: OS={sysname} arch={machine} python={pyver}")

    # OHOS 环境应识别为 HarmonyOS；兼容 Linux 系（部分运行时返回 Linux）
    if sysname not in ("HarmonyOS", "Linux"):
        failures.append(f"unexpected platform.system(): {sysname}")
    # OHOS aarch64 环境
    if machine not in ("aarch64", "arm64"):
        failures.append(f"unexpected platform.machine(): {machine}")
    # Python 版本需满足上游要求 >= 3.10
    major, minor = (int(x) for x in pyver.split(".")[:2])
    if (major, minor) < (3, 10):
        failures.append(f"python version too old: {pyver}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}", file=sys.stderr)
        return 1
    print("ALL CONSUMER TESTS PASSED")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: test_consumer.py <lib_dir>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
