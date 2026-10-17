#!/usr/bin/env python3
"""Conan test_package for qrcodegen — real consumer API test (C++ implementation).

L1 test in the five-level test system. Compiles the consumer probe directly
with the profile's clang++ (argp-standalone pattern), statically linking the
C++ runtime with -static-libstdc++ so the probe only depends on libc.so at
runtime — avoids the OHOS libc++_shared.so search-path problem in conan create's
test stage. CI runs this automatically via `conan create`.

File location: archives/{letter}/qrcodegen/{version}/test_package/conanfile.py
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class QrcodegenTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # argp-standalone/elfutils pattern: compile the consumer probe with
        # clang++ directly (no CMake), linking libqrcodegen.a statically and
        # baking in the C++ runtime via -static-libstdc++.
        dep = self.dependencies["qrcodegen"].cpp_info
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        link = " ".join(["-L" + p for p in libdirs]
                        + ["-l" + l for l in dep.libs])
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cxx = ccs.get("cpp") or os.environ.get("CXX", "clang++")
        # -static-libstdc++: bake libc++ into the probe so runtime only needs
        # system libc.so (skips OHOS libc++_shared.so loader-path issues).
        self.run(f'"{cxx}" {inc} test.cpp -o test_qrcodegen -std=c++11 '
                 f'-static-libstdc++ {link}')

    def test(self):
        # R34: actually execute the probe binary — encodes text/binary/segment
        # payloads through the real library API and asserts QR structure.
        if cross_building(self):
            self.output.info("cross-building: compile+link verified only")
            return
        self.run(os.path.join(self.build_folder, "test_qrcodegen"), env="conanrun")
