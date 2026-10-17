#!/usr/bin/env python3
import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LinuxPamTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        dep = self.dependencies["linux-pam"]
        libdir = dep.cpp_info.libdirs[0] if dep.cpp_info.libdirs else "lib"
        if not os.path.isabs(libdir):
            libdir = os.path.join(dep.package_folder, libdir)

        tc = CMakeToolchain(self)
        tc.variables["LINUX_PAM_TEST_MODULE"] = os.path.join(
            libdir, "security", "pam_permit.so"
        ).replace("\\", "/")
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

        dep = self.dependencies["linux-pam"]
        libdir = dep.cpp_info.libdirs[0] if dep.cpp_info.libdirs else "lib"
        if not os.path.isabs(libdir):
            libdir = os.path.join(dep.package_folder, libdir)

        exe = os.path.join(self.cpp.build.bindirs[0], "test_linux_pam")
        confdir = os.path.join(self.build_folder, "pam.d")
        os.makedirs(confdir, exist_ok=True)
        env = {
            "LD_LIBRARY_PATH": libdir,
            "LINUX_PAM_TEST_CONFDIR": confdir,
        }
        prefix = " ".join("{}={}".format(k, shlex.quote(v)) for k, v in env.items())
        self.run("{} {}".format(prefix, shlex.quote(exe)), env="conanrun")
