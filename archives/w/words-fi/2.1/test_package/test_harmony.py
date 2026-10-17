#!/usr/bin/env python3
"""Build or cross-compile and run the words-fi consumer on an OpenHarmony device."""

import argparse
import logging
import re
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Sequence

LOG = logging.getLogger(__name__)


def validate_device_info(fullname: str, api_level: str, machine: str) -> None:
    """Reject device identities that do not describe a usable OHOS AArch64 target."""
    if not fullname.strip().startswith("OpenHarmony-"):
        raise ValueError(f"unexpected HarmonyOS system name: {fullname!r}")
    api_text = api_level.strip()
    if not re.fullmatch(r"[0-9]+", api_text):
        raise ValueError(f"invalid HarmonyOS API level: {api_level!r}")
    if int(api_text) <= 0:
        raise ValueError(f"invalid HarmonyOS API level: {api_level!r}")
    if machine.strip() != "aarch64":
        raise ValueError(f"expected aarch64 device, got {machine!r}")


def validate_remote_clang(path: str) -> str:
    """Accept only a plain absolute executable path on the HarmonyOS target."""
    if not path.startswith("/") or not re.fullmatch(r"/[A-Za-z0-9/._+-]+", path) or ".." in path.split("/"):
        raise ValueError(f"unsafe remote compiler path: {path!r}")
    return path


def build_remote_test_command(remote_dir: str, remote_clang: str | None = None) -> str:
    """Build the checked consumer on-device when a remote compiler is supplied, then run it."""
    compile_command = ""
    if remote_clang is not None:
        clang = validate_remote_clang(remote_clang)
        compile_command = (
            f"'{clang}' -std=c++17 -Wall -Wextra -Wpedantic "
            "test_words_fi.cpp -o test_words_fi && "
        )
    return (
        f"cd '{remote_dir}' && {compile_command}chmod 700 ./test_words_fi && "
        f"WORDS_FI_FILE='{remote_dir}/words-fi' ./test_words_fi "
        "--require-ohos --expect-machine=aarch64 --expect-count=88328"
    )


def _run(args: Sequence[str], *, capture: bool = True) -> str:
    result = subprocess.run(
        list(args),
        check=False,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        program = Path(args[0]).name
        raise RuntimeError(f"{program} failed with exit code {result.returncode}: {detail}")
    return (result.stdout or "").strip()


def _ssh_args(args: argparse.Namespace, remote_command: str) -> list[str]:
    return [
        "ssh",
        "-i",
        str(args.identity),
        "-p",
        str(args.port),
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=15",
        f"{args.user}@{args.host}",
        remote_command,
    ]


def _read_device_info(args: argparse.Namespace) -> tuple[str, str, str]:
    fullname = _run(_ssh_args(args, "param get const.ohos.fullname"))
    api_level = _run(_ssh_args(args, "param get const.ohos.apiversion"))
    machine = _run(_ssh_args(args, "uname -m"))
    validate_device_info(fullname, api_level, machine)
    return fullname, api_level, machine


def run_device_test(args: argparse.Namespace) -> None:
    if not args.word_list.is_file():
        raise FileNotFoundError(f"word list does not exist or is not a file: {args.word_list}")
    if args.remote_clang:
        validate_remote_clang(args.remote_clang)
        if args.clang is not None or args.sysroot is not None:
            raise ValueError("use either --remote-clang or the local --clang/--sysroot pair")
    else:
        if args.clang is None or args.sysroot is None:
            raise ValueError("provide --remote-clang or both --clang and --sysroot")
        if not args.clang.is_file():
            raise FileNotFoundError(f"compiler does not exist or is not a file: {args.clang}")
        if not args.sysroot.is_dir():
            raise FileNotFoundError(f"sysroot does not exist or is not a directory: {args.sysroot}")
    if not re.fullmatch(r"[A-Za-z0-9.-]+", args.host):
        raise ValueError("--host must be a plain IPv4 address or DNS hostname")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", args.user):
        raise ValueError("--user contains unsupported characters")
    if not 1 <= args.port <= 65535:
        raise ValueError("--port is outside the TCP port range")

    source = Path(__file__).resolve().with_name("test_words_fi.cpp")
    remote_root = args.remote_root.rstrip("/")
    if not remote_root.startswith("/") or not re.fullmatch(r"/[A-Za-z0-9/._-]+", remote_root) or ".." in Path(remote_root).parts:
        raise ValueError(f"unsafe remote root path: {remote_root!r}")
    remote_dir = f"{remote_root}/words-fi-{uuid.uuid4().hex}"
    remote_created = False
    fullname, api_level, machine = _read_device_info(args)
    LOG.info("Device: %s; API %s; %s", fullname, api_level, machine)
    _run(_ssh_args(args, f"mkdir '{remote_dir}'"))
    remote_created = True
    try:
        scp_base = [
            "scp",
            "-i",
            str(args.identity),
            "-P",
            str(args.port),
            "-o",
            "BatchMode=yes",
        ]
        target = f"{args.user}@{args.host}:{remote_dir}/"
        _run([*scp_base, str(args.word_list), target])
        if args.remote_clang:
            _run([*scp_base, str(source), target])
            remote_command = build_remote_test_command(remote_dir, args.remote_clang)
        else:
            with tempfile.TemporaryDirectory(prefix="words-fi-ohos-") as temp_dir:
                binary = Path(temp_dir) / "test_words_fi"
                compile_args = [
                    str(args.clang),
                    "--target=aarch64-linux-ohos",
                    f"--sysroot={args.sysroot}",
                    "-std=c++17",
                    "-Wall",
                    "-Wextra",
                    "-Wpedantic",
                    str(source),
                    "-o",
                    str(binary),
                ]
                _run(compile_args)
                if not binary.is_file():
                    raise RuntimeError("HarmonyOS compiler did not produce the consumer binary")
                _run([*scp_base, str(binary), target])
            remote_command = build_remote_test_command(remote_dir)
        output = _run(_ssh_args(args, remote_command))
        if "HARMONYOS_TEST_OK entries=88328 machine=aarch64" not in output:
            raise RuntimeError(f"HarmonyOS consumer did not report its success marker: {output}")
        LOG.info("%s", output)
    finally:
        if remote_created:
            _run(_ssh_args(args, f"rm -rf '{remote_dir}'"))


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clang", type=Path, help="local HarmonyOS cross-compiler")
    parser.add_argument("--sysroot", type=Path, help="local HarmonyOS sysroot")
    parser.add_argument("--remote-clang", help="absolute path to clang++ on the AArch64 device")
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--identity", type=Path, required=True)
    parser.add_argument("--word-list", type=Path, required=True)
    parser.add_argument("--remote-root", default="/data/local/tmp", help="writable executable temp root on the target")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        run_device_test(_parse_args(argv))
    except (OSError, RuntimeError, ValueError) as exc:
        LOG.error("HarmonyOS words-fi test failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
