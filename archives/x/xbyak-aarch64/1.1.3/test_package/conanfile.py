#!/usr/bin/env python3
"""Conan test_package for xbyak_aarch64 1.1.3 on HarmonyOS PC.

Layer 1 (any host): ohos_abi_check.py inspects the packaged archive without
    executing it - ELF64 AArch64 objects, the public headers, and that the
    library really contains the JIT code-generation implementation (the
    Xbyak_aarch64 symbols for code emission / label resolution).

Layer 2 (can_run only): test_xbyak.cpp is compiled against the packaged
    headers and archive and executed on the HarmonyOS worker.  It JIT-emits
    AArch64 code into executable memory, flushes the instruction cache, calls
    the generated functions and checks the results - the property path C
    claims for this package.
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run


class XbyakAarch64TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xbyak-aarch64 test supports Linux and OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _conf_tool(self, key, default):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get(key, default)

    def test(self):
        pkg = self.dependencies["xbyak-aarch64"].package_folder
        if not pkg:
            raise ConanException("xbyak-aarch64 package folder is not available")

        checker = os.path.join(os.path.dirname(__file__), "ohos_abi_check.py")
        if not os.path.isfile(checker):
            raise ConanException(f"ohos_abi_check.py missing: {checker}")
        self.run(f'python3 "{checker}" --package "{pkg}"', env="conanrun")

        if not can_run(self):
            self.output.info("cross-build host: skipping on-target JIT execution")
            return

        cxx = self._conf_tool("cpp", "clang++")
        src = os.path.join(os.path.dirname(__file__), "test_xbyak.cpp")
        if not os.path.isfile(src):
            raise ConanException(f"test_xbyak.cpp missing: {src}")
        exe = os.path.join(self.build_folder, "test_xbyak")
        inc = os.path.join(pkg, "include")
        lib = os.path.join(pkg, "lib")
        # -std=c++11 matches upstream test flags; the archive is linked
        # statically.
        self.run(
            f'{cxx} -std=c++11 -O2 -I"{inc}" "{src}" -o "{exe}" '
            f'"{lib}/libxbyak_aarch64.a"',
            env="conanrun",
        )
        self.run(f'"{exe}"', env="conanrun")
