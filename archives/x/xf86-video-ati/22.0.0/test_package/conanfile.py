#!/usr/bin/env python3
"""test_package for xf86-video-ati 22.0.0.

Consumer-level test (R34): the package ships two X.Org loadable driver
modules.  The modules resolve their xorg-server symbols from the X server
process that dlopens them, so a standalone program cannot dlopen them on
OHOS (musl binds symbols eagerly at dlopen time — verified on-device: dlopen
fails with "symbol not found" even with RTLD_LAZY).  The test therefore
compiles check_module.c, which validates each packaged module at the ELF
level the same way the X server's module loader identifies a driver:
valid AArch64 shared object, exported atiModuleData/radeonModuleData loader
entry, and an XF86ModuleVersionInfo record with the right driver name and
version (22.0.0).
"""
import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Use the compiler the profile points at (OHOS SDK clang)
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = ccs.get("c") or "clang"
        src = os.path.join(self.source_folder, "check_module.c")
        out = os.path.join(self.build_folder, "check_module")
        self.run(f'"{cc}" "{src}" -o "{out}"')

    def test(self):
        dep = self.dependencies["xf86-video-ati"]
        drivers = os.path.join(dep.package_folder, "lib", "xorg", "modules",
                               "drivers")
        exe = os.path.join(self.build_folder, "check_module")
        self.run(f'"{exe}" "{os.path.join(drivers, "ati_drv.so")}" '
                 f'atiModuleData ati 22 0 0')
        self.run(f'"{exe}" "{os.path.join(drivers, "radeon_drv.so")}" '
                 f'radeonModuleData radeon 22 0 0')
