"""Link with the installed GNU ld, then execute objcopy/strip outputs on OHOS."""
import shlex
import subprocess
import sys
from pathlib import Path


def run(command):
    print("[COMMAND] " + shlex.join(map(str, command)), flush=True)
    result = subprocess.run(command, capture_output=True, text=True)
    print(result.stdout + result.stderr, end="", flush=True)
    print(f"[EXIT] {result.returncode}", flush=True)
    if result.returncode:
        raise RuntimeError(f"native consumer command failed: {command[0]}")
    return result.stdout


def sign_and_run(program):
    # ELF edits invalidate OHOS signatures, so deployment includes re-signing.
    run(["/data/service/hnp/bin/llvm-objcopy", "--remove-section=.codesign", program])
    run(["/data/service/hnp/bin/binary-sign-tool", "sign", "-inFile", program,
         "-outFile", program, "-selfSign", "1"])
    program.chmod(program.stat().st_mode | 0o100)
    output = run([program])
    if output.strip() != "binutils native consumer: 2460":
        raise RuntimeError("native consumer output mismatch")


def main():
    package, output = map(lambda value: Path(value).resolve(), sys.argv[1:3])
    compiler = sys.argv[3]
    output.mkdir(parents=True, exist_ok=True)
    binary = output / "linked"
    copied, stripped = output / "copied", output / "stripped"
    run([compiler, "-fuse-ld=" + str(package / "bin/ld"),
         Path(__file__).with_name("native-consumer.c"), "-o", binary])
    sign_and_run(binary)
    print("[PASS] native installed GNU ld output executes", flush=True)
    run([package / "bin/objcopy", binary, copied])
    sign_and_run(copied)
    print("[PASS] native installed objcopy output executes", flush=True)
    run([package / "bin/strip", "--strip-all", "-o", stripped, binary])
    sign_and_run(stripped)
    print("[PASS] native installed strip output executes", flush=True)


if __name__ == "__main__":
    main()
