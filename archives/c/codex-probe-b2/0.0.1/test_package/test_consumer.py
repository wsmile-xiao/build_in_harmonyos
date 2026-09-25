#!/usr/bin/env python3
"""Consumer test for codex-probe-b2 under OHOS.

Verifies (7 checks, all exercising the packaged dependency API):
  1. provider_probe module import
  2. codex_probe CLI --help
  3. packaged baseline data files reachable and parseable
  4. list-baselines subcommand works locally
  5. audit subcommand surface (--help)
  6. OHOS platform fingerprint
  7. python version satisfies upstream requires-python >= 3.10
"""
import json
import os
import platform
import subprocess
import sys


def main(lib_dir: str) -> int:
    sys.path.insert(0, lib_dir)
    failures = []
    cli = os.path.join(lib_dir, "codex_probe.py")

    # 1. module import
    try:
        import provider_probe  # noqa: F401
        print("PASS: provider_probe import")
    except Exception as e:
        failures.append(f"provider_probe import failed: {e}")

    # 2. CLI --help
    r = subprocess.run([sys.executable, cli, "--help"],
                       capture_output=True, text=True)
    if r.returncode == 0 and "audit" in r.stdout:
        print("PASS: codex_probe.py --help")
    else:
        failures.append(f"--help failed: rc={r.returncode}")

    # 3. baseline data files present and parseable
    try:
        import codex_probe_data
        bdir = os.path.join(os.path.dirname(codex_probe_data.__file__), "baselines")
        js = [f for f in os.listdir(bdir) if f.endswith(".json")]
        assert js, "no baseline JSON packaged"
        with open(os.path.join(bdir, js[0])) as fh:
            data = json.load(fh)
        assert isinstance(data, dict), "baseline JSON shape unexpected"
        print(f"PASS: baselines found and parseable: {len(js)}")
    except Exception as e:
        failures.append(f"baseline data check failed: {e}")

    # 4. list-baselines subcommand
    r = subprocess.run([sys.executable, cli, "list-baselines"],
                       capture_output=True, text=True)
    if r.returncode == 0 and "baseline" in r.stdout.lower():
        print("PASS: list-baselines")
    else:
        failures.append(f"list-baselines failed: rc={r.returncode}")

    # 5. audit subcommand surface
    r = subprocess.run([sys.executable, cli, "audit", "--help"],
                       capture_output=True, text=True)
    if r.returncode == 0 and "--baseline-id" in r.stdout:
        print("PASS: audit --help")
    else:
        failures.append(f"audit --help failed: rc={r.returncode}")

    # 6. platform fingerprint (informational + asserted loosely)
    sysname = platform.system()
    machine = platform.machine()
    print(f"INFO: OS={sysname} arch={machine} python={sys.version.split()[0]}")
    # OHOS 运行时可能返回 HarmonyOS 或 Linux 系值, 二者皆可接受
    if sysname not in ("HarmonyOS", "Linux"):
        failures.append(f"unexpected platform.system(): {sysname}")
    elif machine in ("aarch64", "arm64"):
        print(f"PASS: platform fingerprint ({sysname} {machine})")
    else:
        failures.append(f"unexpected platform.machine(): {machine}")

    # 7. python version >= 3.10 (upstream requires-python)
    pyver = sys.version.split()[0]
    major, minor = (int(x) for x in pyver.split(".")[:2])
    if (major, minor) < (3, 10):
        failures.append(f"python version too old: {pyver}")
    else:
        print(f"PASS: python {pyver} >= 3.10")

    if failures:
        for f in failures:
            print(f"FAIL: {f}", file=sys.stderr)
        return 1
    print("ALL CONSUMER TESTS PASSED")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: test_consumer.py <dep_lib_dir>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
