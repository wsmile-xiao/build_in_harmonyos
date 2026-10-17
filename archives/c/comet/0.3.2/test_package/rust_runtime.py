#!/usr/bin/env python3
"""Prepare signed private Rust tool copies without modifying Conan dependencies.

Same proven scheme as archives/c/cbindgen/0.28.0/test_package/rust_runtime.py:
the rust-toolchain dist binaries lack OHOS execution signatures and Cargo
links libssl/libcrypto dynamically, so cargo/rustc/rustc_driver are copied,
re-signed with the platform binary-sign-tool and executed with a private
LD_LIBRARY_PATH (self-signed copies + relinked OpenSSL DSOs + toolchain lib).
"""

import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def required(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError("Activate the comet Conan environment: missing " + name)
    return value


def tool_environment(root, signed):
    env = os.environ.copy()
    paths = [str(signed), required("COMET_OPENSSL_DIR"), str(root / "lib")]
    if env.get("LD_LIBRARY_PATH"):
        paths.append(env["LD_LIBRARY_PATH"])
    env["LD_LIBRARY_PATH"] = os.pathsep.join(paths)
    return env


def prepare(root):
    identity = (root / "conanmanifest.txt").read_bytes()
    identity += str(root).encode() + Path(__file__).read_bytes()
    key = hashlib.sha256(identity).hexdigest()[:24]
    base = Path(os.environ.get("COMET_RUST_CACHE") or
                str(Path(tempfile.gettempdir()) / "comet-rust-runtime"))
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = base / key
    with (base / (key + ".lock")).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if (target / "ready.json").is_file():
            return target
        temporary = Path(tempfile.mkdtemp(prefix=key + "-", dir=base))
        try:
            sources = [root / "bin/cargo", root / "bin/rustc"]
            sources.extend((root / "lib").glob("librustc_driver-*.so"))
            if len(sources) != 3:
                raise RuntimeError("Expected one rustc driver in the declared Rust package")
            records = []
            for source in sources:
                output = temporary / source.name
                result = subprocess.run(
                    [required("COMET_SIGN_TOOL"), "sign", "-inFile", str(source),
                     "-outFile", str(output), "-selfSign", "1"],
                    capture_output=True, timeout=120)
                if result.returncode or not output.is_file():
                    raise RuntimeError("Rust signing failed: " +
                                       result.stderr.decode(errors="replace")[-2000:])
                output.chmod(0o755)
                records.append({"source": str(source), "size": source.stat().st_size})
            env = tool_environment(root, temporary)
            for name in ("cargo", "rustc"):
                command = [str(temporary / name)]
                if name == "rustc":
                    command += ["--sysroot", str(root)]
                result = subprocess.run(command + ["--version"], env=env,
                                        capture_output=True, timeout=30)
                if result.returncode:
                    raise RuntimeError(name + " probe failed: " +
                                       result.stderr.decode(errors="replace")[-2000:])
            (temporary / "ready.json").write_text(
                json.dumps({"source": str(root), "files": records}), encoding="utf-8")
            os.rename(temporary, target)
        except BaseException:
            shutil.rmtree(temporary)
            raise
    return target


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("cargo", "rustc"):
        raise RuntimeError("Expected cargo or rustc subcommand")
    tool = sys.argv[1]
    root = Path(required("COMET_RUST_ROOT")).resolve()
    signed = prepare(root)
    command = [str(signed / tool)]
    arguments = sys.argv[2:]
    if tool == "rustc" and not any(
            arg == "--sysroot" or arg.startswith("--sysroot=") for arg in arguments):
        command += ["--sysroot", str(root)]
    command += arguments
    os.execve(command[0], command, tool_environment(root, signed))


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print("comet Rust runtime: " + str(error), file=sys.stderr)
        sys.exit(1)
