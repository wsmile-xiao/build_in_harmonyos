#!/usr/bin/env python3
"""Conan test_package for exodriver 2.7.0.

Smoke test: links against liblabjackusb and calls LJUSB_GetLibraryVersion()
to verify the library is usable (R34: test must call the package's API).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class ExodriverTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # R33: get compiler from Conan conf (never bare shell env vars)
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        # Include and lib dirs from the dependency
        exodriver = self.dependencies["exodriver"]
        inc_dir = exodriver.cpp_info.includedirs[0]
        lib_dir = exodriver.cpp_info.libdirs[0]
        libusb = self.dependencies["libusb"]
        libusb_inc = os.path.join(libusb.package_folder, "include")
        libusb_lib = libusb.cpp_info.libdirs[0]

        source = os.path.join(self.source_folder, "test.c")
        output = os.path.join(self.build_folder, "test_exodriver")
        self.run(f'{cc} -o {output} {source} -I{inc_dir} -I{libusb_inc} '
                 f'-L{lib_dir} -L{libusb_lib} '
                 f'-llabjackusb -lusb-1.0 -Wl,-rpath,{lib_dir} -Wl,-rpath,{libusb_lib}')

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.build_folder, "test_exodriver")
            self.run(f'"{bin_path}"', env="conanrun")
