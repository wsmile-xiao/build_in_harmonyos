#!/usr/bin/env python3
"""Conan recipe for continuable 4.2.2, a C++14 header-only library."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout
from conan.tools.scm import Version


required_conan_version = ">=1.52.0"


class ContinuableConan(ConanFile):
    name = "continuable"
    version = "4.2.2"
    description = (
        "C++14 asynchronous allocation aware futures "
        "supporting chaining, exception handling, coroutines and connections"
    )
    license = "MIT"
    homepage = "https://github.com/Naios/continuable"
    url = "https://github.com/Naios/continuable"
    topics = ("asynchronous", "future", "coroutines", "header-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "no_exceptions": [True, False],
        "custom_error_type": [True, False],
        "unhandled_exceptions": [True, False],
        "custom_final_callback": [True, False],
        "immediate_types": [True, False],
    }
    default_options = {
        "no_exceptions": False,
        "custom_error_type": False,
        "unhandled_exceptions": False,
        "custom_final_callback": False,
        "immediate_types": False,
    }
    no_copy_source = True

    @property
    def _min_cppstd(self):
        return 14

    @property
    def _compilers_minimum_version(self):
        return {
            "gcc": "5",
            "clang": "3.4",
            "apple-clang": "10",
            "Visual Studio": "14",
        }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # ohpcd publishes 4.2.3; 4.2.4 is not currently downloadable there.
        # The upstream CMake requirement is function2 major version 4.
        self.requires("function2/4.2.3")

    def package_id(self):
        self.info.clear()

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, self._min_cppstd)
        minimum_version = self._compilers_minimum_version.get(
            str(self.settings.compiler), False
        )
        if minimum_version and Version(self.settings.compiler.version) < minimum_version:
            raise ConanInvalidConfiguration(
                f"{self.ref} requires C++{self._min_cppstd}, "
                "which your compiler does not support."
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # The release archive contains the public headers but empty submodule
        # directories. No library binary is built; this call keeps the recipe
        # patch hook active if a future OHOS-specific patch is required.
        apply_conandata_patches(self)

    def package(self):
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "include", "continuable"),
            dst=os.path.join(self.package_folder, "include", "continuable"),
            keep_path=True,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "continuable")
        self.cpp_info.set_property("cmake_target_name", "continuable::continuable")

        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("pthread")
        if self.options.no_exceptions:
            self.cpp_info.defines.append("CONTINUABLE_WITH_NO_EXCEPTIONS")
        if self.options.custom_error_type:
            self.cpp_info.defines.append("CONTINUABLE_WITH_CUSTOM_ERROR_TYPE")
        if self.options.unhandled_exceptions:
            self.cpp_info.defines.append("CONTINUABLE_WITH_UNHANDLED_EXCEPTIONS")
        if self.options.custom_final_callback:
            self.cpp_info.defines.append("CONTINUABLE_WITH_CUSTOM_FINAL_CALLBACK")
        if self.options.immediate_types:
            self.cpp_info.defines.append("CONTINUABLE_WITH_IMMEDIATE_TYPES")
