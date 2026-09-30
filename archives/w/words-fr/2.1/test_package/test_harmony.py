#!/usr/bin/env python3
"""Build the words-fr HarmonyOS consumer and optionally run an x86_64 OHOS emulator smoke test."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile


TARGETS = {
    "aarch64-linux-ohos": 183,
    "x86_64-linux-ohos": 62,
}


def _wsl_path_for_windows_tool(path: Path, compiler: Path) -> str:
    if not str(compiler).lower().endswith(".exe") or sys.platform != "linux":
        return str(path)
    try:
        release = Path("/proc/sys/kernel/osrelease").read_text(encoding="ascii").lower()
    except OSError:
        return str(path)
    if "microsoft" not in release or not str(path).startswith("/mnt/"):
        return str(path)
    converted = subprocess.run(
        ["wslpath", "-w", str(path)],
        text=True,
        capture_output=True,
        check=False,
    )
    if converted.returncode:
        raise SystemExit(f"wslpath conversion failed for {path}: {converted.stderr}")
    return converted.stdout.strip()


def _run_harmony_emulator(
    hdc: Path,
    device: str,
    binary: Path,
    word_list: Path,
) -> None:
    remote_dir = "/data/local/tmp/words-fr-2.1-test"
    remote_binary = f"{remote_dir}/test_words_fr"
    remote_words = f"{remote_dir}/words-fr"

    def run_hdc(args: list[str], label: str) -> str:
        result = subprocess.run(args, text=True, capture_output=True, errors="replace")
        output = (result.stdout or "") + (result.stderr or "")
        if result.returncode:
            raise SystemExit(f"{label} failed (rc={result.returncode}):\n{output}")
        return output

    if not hdc.is_file():
        raise SystemExit(f"hdc not found: {hdc}")
    if not word_list.is_file():
        raise SystemExit(f"Conan word list not found: {word_list}")

    run_hdc([str(hdc), "-t", device, "shell", f"mkdir -p {remote_dir}"], "HDC mkdir")
    run_hdc([str(hdc), "-t", device, "file", "send", str(binary), remote_binary], "HDC binary push")
    run_hdc([str(hdc), "-t", device, "file", "send", str(word_list), remote_words], "HDC data push")
    command = (
        f"chmod 755 {remote_binary} && "
        f"WORDS_FR_FILE={remote_words} {remote_binary} "
        "--require-ohos --expect-machine=x86_64"
    )
    try:
        output = run_hdc([str(hdc), "-t", device, "shell", command], "HarmonyOS consumer")
        if "WORDS_FR_HARMONY_OK entries=629569 machine=x86_64" not in output:
            raise SystemExit(f"HarmonyOS emulator did not report the expected result:\n{output}")
        print("HARMONYOS_X86_64_RUNTIME_OK entries=629569 machine=x86_64")
    finally:
        subprocess.run(
            [
                str(hdc),
                "-t",
                device,
                "shell",
                f"rm -f {remote_binary} {remote_words} && rmdir {remote_dir}",
            ],
            text=True,
            capture_output=True,
            errors="replace",
            check=False,
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=TARGETS, default="aarch64-linux-ohos")
    parser.add_argument("--clang", type=Path, required=True)
    parser.add_argument("--sysroot", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--run-device", action="store_true")
    parser.add_argument("--hdc", type=Path)
    parser.add_argument("--device", default="127.0.0.1:5555")
    parser.add_argument("--word-list", type=Path)
    args = parser.parse_args()

    if not args.clang.is_file():
        raise SystemExit(f"clang++ not found: {args.clang}")
    if args.sysroot is not None and not args.sysroot.is_dir():
        raise SystemExit(f"OHOS sysroot not found: {args.sysroot}")
    if args.run_device and args.target != "x86_64-linux-ohos":
        raise SystemExit("the available x86_64 emulator can run only x86_64-linux-ohos binaries")
    if args.run_device and args.hdc is None:
        raise SystemExit("--run-device requires --hdc")

    source = Path(__file__).with_name("test_words_fr.cpp")
    if args.output:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        temp_context = None
    else:
        temp_context = tempfile.TemporaryDirectory(prefix="words-fr-ohos-consumer-")
        output = Path(temp_context.name) / "test_words_fr"

    macros = ["-DWORDS_FR_REQUIRE_OHOS=1"]
    if args.target == "aarch64-linux-ohos":
        macros.append("-DWORDS_FR_REQUIRE_AARCH64=1")
    compiler_arg = str(args.clang)
    source_arg = _wsl_path_for_windows_tool(source, args.clang)
    output_arg = _wsl_path_for_windows_tool(output, args.clang)
    sysroot_arg = _wsl_path_for_windows_tool(args.sysroot, args.clang) if args.sysroot is not None else None
    command = [
        compiler_arg,
        f"--target={args.target}",
        *([f"--sysroot={sysroot_arg}"] if sysroot_arg else []),
        "-std=c++17",
        "-O2",
        "-Wall",
        "-Wextra",
        "-Werror",
        *macros,
        source_arg,
        "-o",
        output_arg,
    ]
    completed = subprocess.run(command, text=True, capture_output=True, errors="replace")
    if completed.returncode:
        raise SystemExit(
            f"HarmonyOS consumer compilation failed for {args.target}:\n"
            + completed.stdout
            + completed.stderr
        )

    elf = output.read_bytes()
    if len(elf) < 20 or elf[:4] != b"\x7fELF" or elf[4] != 2 or elf[5] != 1:
        raise SystemExit("compiler output is not a little-endian ELF64 binary")
    machine = int.from_bytes(elf[18:20], "little")
    expected_machine = TARGETS[args.target]
    if machine != expected_machine:
        raise SystemExit(
            f"compiler output ELF machine={machine}, expected {args.target} ({expected_machine})"
        )
    print(f"HARMONYOS_COMPILE_OK target={args.target} elf_machine={machine} output={output}")

    if args.run_device:
        assert args.hdc is not None
        assert args.word_list is not None
        if args.target != "x86_64-linux-ohos":
            raise SystemExit("device runtime is intentionally limited to the x86_64 emulator")
        _run_harmony_emulator(args.hdc, args.device, output, args.word_list)
    elif args.word_list is not None and args.target == "aarch64-linux-ohos":
        print("AArch64 consumer compiled; no AArch64 runtime was requested or available.")

    if temp_context is not None:
        temp_context.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
