#!/usr/bin/env python3
import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class NssWrapperTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        dep = self.dependencies["nss-wrapper"]
        libdir = dep.cpp_info.libdirs[0] if dep.cpp_info.libdirs else "lib"
        libname = "libnss_wrapper.so"
        tc = CMakeToolchain(self)
        tc.variables["NSS_WRAPPER_TEST_LIBRARY"] = os.path.join(
            dep.package_folder, libdir, libname
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
        dep = self.dependencies["nss-wrapper"]
        libdir = dep.cpp_info.libdirs[0] if dep.cpp_info.libdirs else "lib"
        if not os.path.isabs(libdir):
            libdir = os.path.join(dep.package_folder, libdir)
        lib_path = os.path.join(libdir, "libnss_wrapper.so")
        passwd_path = os.path.join(self.build_folder, "passwd")
        group_path = os.path.join(self.build_folder, "group")
        exe = os.path.join(self.cpp.build.bindirs[0], "test_nss_wrapper")
        env = {
            "LD_PRELOAD": lib_path,
            "LD_LIBRARY_PATH": libdir,
            "NSS_WRAPPER_PASSWD": passwd_path,
            "NSS_WRAPPER_GROUP": group_path,
            "NSS_WRAPPER_HOSTNAME": "nss-wrapper-ohos-test",
        }
        prefix = " ".join("{}={}".format(k, shlex.quote(v)) for k, v in env.items())
        self.run("{} {}".format(prefix, shlex.quote(exe)), env="conanrun")
