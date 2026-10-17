#!/usr/bin/env python3
"""test_package — verifies the installed libelfin package.

The test binary parses its own on-disk image through the installed headers and
both installed libraries, then the recipe asserts the shipped pkg-config
metadata.  Full DWARFv4 parsing is covered by the upstream suite that the
recipe runs during build().
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibelfinTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    generators = "CMakeToolchain", "CMakeDeps"

    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        # e_machine values for the architectures the OHOS profile may select;
        # 0 means "do not assert the machine" (the test still checks parity of
        # the ELF header, section table, symbol table and DWARF sections).
        emachines = {"armv8": 183, "x86_64": 62, "x86": 3, "armv7": 40}
        cmake.configure(
            variables={
                "LIBELFIN_EXPECT_MACHINE": emachines.get(str(self.settings.arch), 0)
            }
        )
        cmake.build()

    def test(self):
        # The shipped pkg-config files must describe this exact version.
        pkg_dir = self.dependencies["libelfin"].package_folder
        for pc_name, requires in (
            ("libelf++.pc", None),
            ("libdwarf++.pc", "Requires: libelf++ ="),
        ):
            pc_file = os.path.join(pkg_dir, "lib", "pkgconfig", pc_name)
            self.output.info(f"checking {pc_file}")
            assert os.path.isfile(pc_file), f"missing {pc_name}"
            content = open(pc_file, encoding="utf-8").read()
            assert "Version: 0.3.r7.ge017276" in content, f"{pc_name} version"
            if requires:
                assert requires in content, f"{pc_name} dependency"

        if can_run(self):
            self.run(
                os.path.join(self.cpp.build.bindir, "test_libelfin"),
                env="conanrun",
            )
