"""Run one native OHOS-specific minunit timer test; never pass on a host."""
import argparse
import os
import shutil
from pathlib import Path
import subprocess
import tempfile


def main():
    p = argparse.ArgumentParser()
    p.add_argument("package")
    p.add_argument("--compiler", required=True)
    p.add_argument("--signer")
    p.add_argument("--work-root")
    a = p.parse_args()
    if not hasattr(os, "uname") or os.uname().sysname != "HarmonyOS":
        raise SystemExit("FAIL: HarmonyOS target execution required")
    if os.uname().machine not in ("aarch64", "arm64"):
        raise SystemExit("FAIL: real aarch64 target required")
    header = Path(a.package) / "include" / "minunit.h"
    if not header.is_file():
        raise SystemExit("FAIL: installed minunit header missing")
    work_root = Path(a.work_root or os.environ.get("TMPDIR") or os.getcwd()).resolve()
    if not work_root.is_dir():
        raise SystemExit("FAIL: existing task work directory required")
    with tempfile.TemporaryDirectory(prefix="minunit-ohos-", dir=str(work_root)) as td:
        child_env = dict(os.environ, TMPDIR=td, TMPPREFIX=str(Path(td) / "tmp"))
        binary = str(Path(td) / "timer_backend")
        src = str(Path(__file__).with_name("timer_backend.c"))
        subprocess.run([a.compiler, src, "-I" + str(header.parent), "-std=c11",
                        "-o", binary, "-lm"], check=True, timeout=60, env=child_env)
        signer = a.signer or shutil.which("binary-sign-tool")
        if not signer:
            raise SystemExit("FAIL: native OHOS signer is required")
        if signer:
            signed = binary + ".signed"
            subprocess.run([signer, "sign", "-inFile", binary,
                            "-outFile", signed, "-selfSign", "1"], check=True, timeout=30, env=child_env)
            os.chmod(signed, 0o700)
            binary = signed
        r = subprocess.run([binary], capture_output=True, text=True, timeout=10, env=child_env)
        print(r.stdout, end="")
        print(r.stderr, end="")
        if r.returncode != 0 or "1 tests, 4 assertions, 0 failures" not in r.stdout:
            raise SystemExit("FAIL: OHOS timer backend test did not pass exact denominator")
    print("HARMONY_TEST_PASS=1/1")


if __name__ == "__main__":
    main()
