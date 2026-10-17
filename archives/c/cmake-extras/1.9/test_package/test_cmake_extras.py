#!/usr/bin/env python3
"""Conan test_package for cmake-extras — R34 real artifact verification.

cmake-extras is a pure CMake-module data package: no compiled artifact, no
executable. The verifiable artifact is the set of CMake module directories
under <pkg>/share/cmake/ (CopyrightTest, GDbus, GSettings, GdbusCodegen,
Intltool, Vala, ...). R34 asserts these module dirs exist — the modules a
consuming CMake project would find_package()/include() — plus the package
carries at least one actual .cmake file (real content, not just empty dirs).
"""
import os
import sys


EXPECTED = ["CopyrightTest", "CoverageReport", "DoxygenBuilder", "GDbus",
            "GMock", "GObjectIntrospection", "GSettings", "GdbusCodegen",
            "Intltool", "Lcov", "Vala", "gcovr"]


def main():
    pkg = sys.argv[1]
    base = os.path.join(pkg, "share", "cmake")
    if not os.path.isdir(base):
        print(f"FAIL: {base} not found", file=sys.stderr)
        return 1
    found = set(os.listdir(base))
    for name in EXPECTED:
        if name not in found:
            print(f"FAIL: module dir {name} not under {base}", file=sys.stderr)
            return 1
    # R34: 至少一个模块目录含真实 .cmake 文件（非空壳目录）
    has_cmake = any(
        os.path.isfile(os.path.join(base, name, f))
        for name in found
        for f in os.listdir(os.path.join(base, name))
        if f.endswith(".cmake")
    )
    if not has_cmake:
        print("FAIL: no .cmake files under share/cmake/", file=sys.stderr)
        return 1
    print(f"OK: cmake-extras modules present: {len(found)} dirs, {EXPECTED.count(1)} expected + .cmake content")
    return 0


if __name__ == "__main__":
    sys.exit(main())
