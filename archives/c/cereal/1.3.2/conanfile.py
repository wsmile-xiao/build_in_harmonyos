#!/usr/bin/env python3
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.files import copy, export_conandata_patches, get
import os


class CerealConan(ConanFile):
    name = "cereal"
    version = "1.3.2"
    description = "C++11 header-only serialization library"
    license = "BSD-3-Clause"
    homepage = "https://uscilab.github.io/cereal/"
    url = "https://github.com/USCiLab/cereal"
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"thread_safe": [True, False]}
    default_options = {"thread_safe": False}

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, "11")
        if self.settings.os not in ("Linux", "OHOS", "Windows", "Macos", "FreeBSD"):
            raise ConanInvalidConfiguration(f"{self.ref} has not been validated for {self.settings.os}")

    def package(self):
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "include", "cereal"),
            dst=os.path.join(self.package_folder, "include", "cereal"),
        )
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        del self.info.settings.os
        del self.info.settings.compiler
        del self.info.settings.build_type
        del self.info.settings.arch

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "cereal")
        self.cpp_info.set_property("cmake_target_name", "cereal::cereal")
        if self.options.thread_safe:
            self.cpp_info.defines.append("CEREAL_THREAD_SAFE=1")
            if self.settings.os in ("Linux", "OHOS", "FreeBSD"):
                self.cpp_info.system_libs.append("pthread")
