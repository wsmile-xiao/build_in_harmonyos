#!/usr/bin/env python3
"""Validate packaged WASI runtime assets."""
import json
import os
import sys


def fail(message):
    raise SystemExit(message)


def assert_nonempty_file(path):
    if not os.path.isfile(path):
        fail(f"Missing WASI runtime asset: {path}")
    if os.path.getsize(path) <= 0:
        fail(f"Empty WASI runtime asset: {path}")


def assert_contains(path, marker):
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        content = handle.read()
    if marker not in content:
        fail(f"WASI header {path} did not contain expected marker {marker!r}")


def assert_archive(path):
    with open(path, "rb") as handle:
        magic = handle.read(8)
    if magic != b"!<arch>\n":
        fail(f"WASI archive {path} has unexpected magic {magic!r}")


def load_manifest(root):
    manifest_path = os.path.join(root, "share", "wasi-sysroot", ".wasi-assets.json")
    if not os.path.isfile(manifest_path):
        fail(f"Missing WASI asset manifest: {manifest_path}")
    with open(manifest_path, "r", encoding="utf-8") as handle:
        assets = json.load(handle)
    if not isinstance(assets, list) or not assets:
        fail("WASI asset manifest is not a non-empty list")
    return assets


def assert_manifest_complete(root, assets):
    sysroot = os.path.join(root, "share", "wasi-sysroot")
    checked = 0
    for entry in assets:
        rel_path = entry.get("path")
        expected_size = entry.get("size")
        if not isinstance(rel_path, str) or not rel_path:
            fail("WASI asset manifest entry is missing path")
        if not isinstance(expected_size, int) or expected_size < 0:
            fail(f"WASI asset manifest entry has invalid size for {rel_path!r}")
        full_path = os.path.join(sysroot, rel_path)
        if not os.path.isfile(full_path):
            fail(f"Missing packaged WASI asset: {rel_path}")
        actual_size = os.path.getsize(full_path)
        if actual_size != expected_size:
            fail(f"WASI asset size mismatch for {rel_path}: expected {expected_size}, got {actual_size}")
        checked += 1
    return checked


def main(argv):
    if len(argv) != 2:
        fail("usage: check_wasi_assets.py <package_folder>")
    root = argv[1]
    wasi_stdio = os.path.join(root, "share", "wasi-sysroot", "include", "wasm32-wasi", "stdio.h")
    wasip2_stdlib = os.path.join(root, "share", "wasi-sysroot", "include", "wasm32-wasip2", "stdlib.h")
    libc = os.path.join(root, "share", "wasi-sysroot", "lib", "wasm32-wasi", "libc.a")
    builtins = os.path.join(root, "share", "wasi-sysroot", "lib", "wasm32-wasi", "libclang_rt.builtins-wasm32.a")

    assets = load_manifest(root)
    checked = assert_manifest_complete(root, assets)

    for path in (wasi_stdio, wasip2_stdlib, libc, builtins):
        assert_nonempty_file(path)
    assert_contains(wasi_stdio, "FILE")
    assert_contains(wasip2_stdlib, "malloc")
    assert_archive(libc)
    assert_archive(builtins)
    print(f"WASI runtime assets packaged and structurally validated ({checked} files from official wasi-sdk-25 archives)")


if __name__ == "__main__":
    main(sys.argv)
