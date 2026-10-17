#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for PC-ALE — Open Source ALE for Amateur Radio.

HarmonyOS PC (aarch64) adaptation.
"""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get
import os

class PcaleConan(ConanFile):
    name = "pcale"
    version = "3.0.0"
    package_type = "library"
    license = "MIT"
    homepage = "https://github.com/Alex-Pennington/PC-ALE"
    url = "https://github.com/Alex-Pennington/PC-ALE"
    description = "PC-ALE - Open Source ALE (Automatic Link Establishment) for Amateur Radio"
    topics = ("radio", "ham", "ALE", "HF", "communication")
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    generators = "CMakeDeps"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        # Install headers
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        # Install built libraries from build folder
        build_dir = os.path.join(self.build_folder, self.cpp.build.bindir) if self.cpp.build.bindir else self.build_folder
        copy(self, "*.a", src=build_dir, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.so", src=build_dir, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.lib", src=build_dir, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.dylib", src=build_dir, dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        # Upstream builds multiple libraries: ale_fsk_core, ale_fec, ale_protocol,
        # ale_aqc, ale_link, ale_fs1052, ale_lqa
        self.cpp_info.libs = ["ale_fsk_core", "ale_fec", "ale_protocol",
                              "ale_aqc", "ale_link", "ale_fs1052", "ale_lqa"]
        self.cpp_info.includedirs = ["include"]
        if self.settings.os in ["Linux", "OHOS"]:
            self.cpp_info.system_libs = ["pthread"]
