#!/usr/bin/env python3
"""Conan recipe — afmize 2.0.2 (CMake)."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class AfmizeConan(ConanFile):
    name = "afmize"
    version = "2.0.2"
    package_type = "application"
    license = "MIT"
    homepage = "https://github.com/ToruNiina/afmize"
    url = "https://github.com/ToruNiina/afmize"
    description = "Atomic force microscopy image simulator"
    topics = ("afm", "molecular", "simulation")
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*", "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("boost/1.84.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        data = self.conan_data["sources"][self.version]
        get(self, **{k: data[k] for k in ("url", "sha256")}, strip_root=True)
        # The release tarball has empty submodule directories. Inject each
        # pinned snapshot locally; no git or network access occurs in CMake.
        for name, sub in data["submodules"].items():
            get(self, **sub, destination="extlib/" + name, strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # CMake has no OHOS platform module; OHOS clang is Linux-compatible.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            # Boost.Test's pthread cancellation guard is not declared by the
            # OHOS libc headers, although the rest of Boost is usable.
            tc.preprocessor_definitions["BOOST_SP_NO_PTHREAD_SETCANCELSTATE"] = "1"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"], build_tool_args=["-j1"])
        cmake.test(cli_args=["--parallel", "1"], build_tool_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", self.package_folder + "/bin")
