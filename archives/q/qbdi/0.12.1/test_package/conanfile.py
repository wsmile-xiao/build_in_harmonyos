#!/usr/bin/env python3
"""Conan test_package for QBDI 0.12.1 on HarmonyOS PC.

Layer 1 (any host): ohos_abi_check.py inspects the packaged archive without
    executing it - ELF64 AArch64 objects, the public QBDI headers, and that the
    private LLVM really is inside libQBDI.a (LLVM symbols), which is the whole
    point of this package.

Layer 2 (can_run only): test_qbdi.cpp links against the packaged libQBDI.a and
    drives the **embedded in-process VM** on the HarmonyOS worker: it
    instruments a function of the test binary itself, checks the function's
    return value is preserved, and checks the PREINST callback actually fires.
    It deliberately does not use ptrace / external attach.
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run


class QBDITestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"QBDI test supports Linux and OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _conf_tool(self, key, default):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get(key, default)

    def test(self):
        pkg = self.dependencies["qbdi"].package_folder
        if not pkg:
            raise ConanException("qbdi package folder is not available")

        checker = os.path.join(os.path.dirname(__file__), "ohos_abi_check.py")
        if not os.path.isfile(checker):
            raise ConanException(f"ohos_abi_check.py missing: {checker}")
        self.run(f'python3 "{checker}" --package "{pkg}"', env="conanrun")

        if not can_run(self):
            self.output.info("cross-build host: skipping on-target VM execution")
            return

        cxx = self._conf_tool("cpp", "clang++")
        src = os.path.join(os.path.dirname(__file__), "test_qbdi.cpp")
        if not os.path.isfile(src):
            raise ConanException(f"test_qbdi.cpp missing: {src}")
        exe = os.path.join(self.build_folder, "test_qbdi")
        inc = os.path.join(pkg, "include")
        lib = os.path.join(pkg, "lib")
        self.run(
            f'{cxx} -std=c++17 -O1 -I"{inc}" "{src}" -o "{exe}" '
            f'-L"{lib}" -lQBDI -lpthread -ldl -lm',
            env="conanrun",
        )
        self.run(f'"{exe}"', env="conanrun")
