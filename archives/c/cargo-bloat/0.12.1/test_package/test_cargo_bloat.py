#!/usr/bin/env python3
"""Run cargo-bloat against a tiny, dependency-free Rust executable."""

import os
import shutil
import subprocess
import sys
import tempfile


_TOOLCHAIN_ENV = None
_TOOLCHAIN_SHIM_DIR = None


def cleanup_toolchain_env():
    global _TOOLCHAIN_SHIM_DIR
    if _TOOLCHAIN_SHIM_DIR:
        shutil.rmtree(_TOOLCHAIN_SHIM_DIR, ignore_errors=True)
        _TOOLCHAIN_SHIM_DIR = None


def toolchain_env():
    global _TOOLCHAIN_ENV, _TOOLCHAIN_SHIM_DIR
    if _TOOLCHAIN_ENV is not None:
        return _TOOLCHAIN_ENV.copy()
    env = os.environ.copy()
    root = os.path.join(os.path.dirname(__file__), "rust-toolchain")
    cargo_real = None
    libs = []
    for directory, _dirs, files in os.walk(root):
        if os.path.basename(directory) == "bin" and "cargo.real" in files:
            cargo_real = os.path.join(directory, "cargo.real")
        if os.path.basename(directory) == "lib" and {"libssl.so", "libcrypto.so", "libz.so"} & set(files):
            libs.append(directory)
    if cargo_real:
        shim_dir = tempfile.mkdtemp(prefix="cargo-bloat-toolchain-", dir=env.get("TMPDIR") or None)
        _TOOLCHAIN_SHIM_DIR = shim_dir
        shim = os.path.join(shim_dir, "cargo")
        shutil.copy2(cargo_real, shim)
        os.chmod(shim, 0o750)
        env["PATH"] = os.pathsep.join([shim_dir, env.get("PATH", "")])
    if libs:
        env["LD_LIBRARY_PATH"] = os.pathsep.join(libs + ([env["LD_LIBRARY_PATH"]] if env.get("LD_LIBRARY_PATH") else []))
    _TOOLCHAIN_ENV = env
    return env.copy()


def run(binary, *args, cwd=None):
    env = toolchain_env()
    env["PATH"] = os.path.dirname(binary) + os.pathsep + env.get("PATH", "")
    result = subprocess.run(
        [binary, "bloat", *args], cwd=cwd, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"{binary} bloat {' '.join(args)} failed ({result.returncode})\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def main():
    if len(sys.argv) != 3:
        print("usage: test_cargo_bloat.py <cargo-bloat> <Cargo.toml>", file=sys.stderr)
        return 2
    try:
        binary, manifest = sys.argv[1:]
        version = run(binary, "--version")
        assert version.stdout.strip() == "0.12.1", version.stdout
        help_output = run(binary, "--help").stdout
        assert "--crates" in help_output and "--message-format" in help_output
        analysis = run(
            binary, "--release", "--crates", "--filter", "fixture",
            "--message-format", "json", "--manifest-path", manifest, "-n", "5",
            cwd=os.path.dirname(manifest),
        )
        assert "cargo_bloat" in analysis.stdout or "fixture" in analysis.stdout
        print("cargo-bloat version/help/ELF analysis checks passed")
        return 0
    finally:
        cleanup_toolchain_env()


if __name__ == "__main__":
    sys.exit(main())
