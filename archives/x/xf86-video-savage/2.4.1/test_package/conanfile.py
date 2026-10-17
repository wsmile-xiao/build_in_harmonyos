#!/usr/bin/env python3
"""Conan test_package for xf86-video-savage 2.4.1.

Verifies the built savage_drv.so driver module:
  - valid ELF64 AArch64 shared object
  - dynamic symbol table exports the symbols the X server loader
    requires (savageModuleData, the DriverRec, and VBE entry points)

The driver is a loadable X.Org module: its server-side symbols
(xf86*, pci_device_*, VBE*) are resolved by the X server at runtime,
so the test inspects the module's dynamic symbol table instead of
dlopen()-ing it (there is no X server in the test environment).
"""
import os

from conan import ConanFile
from conan.tools.files import copy


class Xf86VideoSavageTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Locate the driver module inside the tested package
        dep = self.dependencies["xf86-video-savage"]
        module_dir = os.path.join(dep.package_folder, "lib", "xorg",
                                  "modules", "drivers")

        # Compile the test program with the profile compiler
        cc_info = self.conf_info.get("tools.build:compiler_executables")
        cc = cc_info["c"] if cc_info and "c" in cc_info else "clang"
        test_src = os.path.join(os.path.dirname(__file__), "test_savage.c")
        test_bin = os.path.join(self.build_folder, "test_savage")
        self.run(f'{cc} -fPIC -O2 -o "{test_bin}" "{test_src}"', env="conanbuild")

        # Keep the module path for test()
        self._module = os.path.join(module_dir, "savage_drv.so")
        copy(self, "savage_drv.so", src=module_dir,
             dst=self.build_folder, keep_path=False)

    def test(self):
        so_path = os.path.join(self.build_folder, "savage_drv.so")
        if not os.path.isfile(so_path):
            raise Exception(f"savage_drv.so not found in package output")
        test_bin = os.path.join(self.build_folder, "test_savage")
        self.run(f'"{test_bin}" "{so_path}"', env="conanrun")
