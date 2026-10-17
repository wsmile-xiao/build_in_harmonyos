#!/usr/bin/env python3
"""Conan test_package — efivar 39.

Compiles a small C program that links against libefivar and calls
efi_get_libefivar_version(), efi_str_to_guid(), efi_guid_is_empty(),
efi_guid_to_str() and efi_guid_cmp() to verify the library is
functional (R34: test genuinely exercises the API). Additionally
smokes the installed efivar CLI tool (-L lists well-known GUIDs).
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class EfivarTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            # OHOS: wrap with CONFIG_SHELL bash and assemble LD_LIBRARY_PATH
            # explicitly from every dependency libdir (loader cannot find
            # libefivar.so.1 via conanrun alone).
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            libs = []
            for _ref, _dep in self.dependencies.items():
                libs += list(_dep.cpp_info.libdirs)
            ld_path = ":".join(dict.fromkeys(l for l in libs if l))
            exe = os.path.join(self.cpp.build.bindirs[0], "test_efivar")
            self.run(
                f'{bash} -c \'export LD_LIBRARY_PATH="{ld_path}"; "{exe}"\'',
                env="conanrun",
            )

            # Smoke the installed efivar CLI tool: -L prints the well-known
            # GUID table (exercises libefivar.so at runtime via the binary).
            bindir = self.dependencies["efivar"].cpp_info.bindirs[0]
            efivar_bin = os.path.join(
                self.dependencies["efivar"].package_folder, bindir, "efivar"
            )
            self.run(
                f'{bash} -c \'export LD_LIBRARY_PATH="{ld_path}"; "{efivar_bin}" -L | grep -q grub\'',
                env="conanrun",
            )
            print("efivar CLI smoke (-L | grep grub): OK")
        else:
            self.output.info("cross-building: consumer linked but cannot run")
