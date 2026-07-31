#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class NssWrapperConan(ConanFile):
    name = "nss-wrapper"
    version = "1.1.16"
    description = "A wrapper for testing applications that use libc NSS calls"
    license = "BSD-3-Clause"
    homepage = "https://cwrap.org/nss_wrapper.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True], "with_upstream_tests": [True, False]}
    default_options = {"shared": True, "with_upstream_tests": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "nss-wrapper requires POSIX libc NSS/nsswitch and LD_PRELOAD support"
            )

    def requirements(self):
        if self.options.with_upstream_tests:
            self.requires("cmocka/2.0.2")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        if self.options.with_upstream_tests:
            deps = CMakeDeps(self)
            deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["UNIT_TESTING"] = bool(self.options.with_upstream_tests)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.with_upstream_tests:
            self.run("ctest --output-on-failure", cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        lib_path = os.path.join(self.package_folder, "lib", "libnss_wrapper.so")
        self.cpp_info.set_property("cmake_file_name", "nss_wrapper")
        self.cpp_info.set_property("cmake_target_name", "nss_wrapper::nss_wrapper")
        self.cpp_info.set_property("pkg_config_name", "nss_wrapper")
        self.cpp_info.libs = ["nss_wrapper"]
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.define_path("NSS_WRAPPER_LIB", lib_path)
        self.buildenv_info.define_path("NSS_WRAPPER_LIB", lib_path)
        self.runenv_info.append_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
