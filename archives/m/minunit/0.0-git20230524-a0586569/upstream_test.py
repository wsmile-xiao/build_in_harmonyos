"""Build and execute minunit's unchanged official CI regression harness."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess


def main():
    p = argparse.ArgumentParser()
    p.add_argument("source")
    p.add_argument("build")
    p.add_argument("--compiler", required=True)
    p.add_argument("--signer")
    a = p.parse_args()
    source, build = Path(a.source), Path(a.build)
    build.mkdir(parents=True, exist_ok=True)
    windows = os.name == "nt"
    binary = build / ("minunit_example.exe" if windows else "minunit_example")
    subprocess.run([a.compiler, str(source / "minunit_example.c"),
                    "-I" + str(source), "-o", str(binary), "-lm"],
                   check=True, timeout=60)
    ohos = hasattr(os, "uname") and os.uname().sysname == "HarmonyOS"
    signer = a.signer or (shutil.which("binary-sign-tool") if ohos else None)
    if ohos and not signer:
        raise SystemExit("FAIL: OHOS upstream execution requires a native signer")
    if signer:
        signed = str(binary) + ".signed"
        subprocess.run([signer, "sign", "-inFile", str(binary),
                        "-outFile", signed, "-selfSign", "1"], check=True, timeout=30)
        os.chmod(signed, 0o700)
        os.replace(signed, binary)
    # Preserve the upstream harness bytes, including its expected exit code 6.
    script = source / "ci" / ("check_example.bat" if windows else "check_example.sh")
    local_script = build / script.name
    shutil.copyfile(script, local_script)
    # The unchanged script uses only POSIX shell constructs, not Bash syntax.
    command = ["cmd", "/c", str(local_script)] if windows else ["sh", str(local_script)]
    r = subprocess.run(command, cwd=build, capture_output=True, text=True, timeout=10)
    print(r.stdout, end="")
    print(r.stderr, end="")
    if r.returncode != 0 or "11 tests, 11 assertions, 6 failures" not in r.stdout:
        raise SystemExit("FAIL: official expected-failure harness did not pass")
    expected = ["test_check_fail", "test_assert_fail", "test_assert_int_eq_fail",
                "test_assert_double_eq_fail", "test_string_eq_fail", "test_fail"]
    if any(r.stdout.count(name + " failed:") != 1 for name in expected):
        raise SystemExit("FAIL: expected upstream failure identities changed")
    print("UPSTREAM_TEST_PASS=1/1 (official harness; 11 sample cases, 6 expected failures)")


if __name__ == "__main__":
    main()
