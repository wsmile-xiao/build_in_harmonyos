#!/usr/bin/env python3
import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class UidWrapperTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["uid-wrapper"]
        libdir = dep.cpp_info.libdirs[0] if dep.cpp_info.libdirs else "lib"
        if not os.path.isabs(libdir):
            libdir = os.path.join(dep.package_folder, libdir)

        exe = os.path.join(self.cpp.build.bindirs[0], "test_uid_wrapper")
        runtime_dir = os.path.join(self.build_folder, "runtime")
        os.makedirs(runtime_dir, exist_ok=True)

        env = {
            "LD_PRELOAD": os.path.join(libdir, "libuid_wrapper.so"),
            "LD_LIBRARY_PATH": libdir,
            "UID_WRAPPER": "1",
            "UID_WRAPPER_ROOT": "1",
            "TMPDIR": runtime_dir,
        }
        prefix = " ".join("{}={}".format(k, shlex.quote(v)) for k, v in env.items())
        self.run("{} {}".format(prefix, shlex.quote(exe)), env="conanrun")
