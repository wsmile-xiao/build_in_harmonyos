#!/usr/bin/env python3
"""Conan recipe for libgooglepinyin 0.1.2 on HarmonyOS PC (CMake).

The upstream data/ step runs the freshly compiled ``dictbuilder`` executable
to convert the raw UTF-16 dictionary text into the binary ``dict_pinyin.dat``.
A cross build cannot execute a target-ABI tool on the build machine, so the
recipe always builds a build-machine ``dictbuilder`` in a plain CMake pass,
generates the dictionary with it, and lets the patched ``data/CMakeLists.txt``
install that prebuilt file instead of running the target tool.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibgooglepinyinConan(ConanFile):
    name = "libgooglepinyin"
    version = "0.1.2"
    description = (
        "Google Pinyin IME decoding engine library, forked from the Android "
        "AOSP Google Pinyin input method"
    )
    license = "Apache-2.0"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    homepage = "https://code.google.com/archive/p/libgooglepinyin/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["ENABLE_STATIC"] = not bool(self.options.shared)
        toolchain.generate()

    def _host_jobs(self):
        return self.conf.get("tools.build:jobs", default=2)

    def _build_host_dictionary(self):
        """Generate the binary dictionary with a build-machine dictbuilder."""
        source_dir = self.source_folder
        host_dir = os.path.join(self.build_folder, "host-pass")
        jobs = self._host_jobs()
        self.run(
            f'cmake -S "{source_dir}" -B "{host_dir}" '
            f"-DCMAKE_BUILD_TYPE={self.settings.build_type} -DENABLE_STATIC=ON"
        )
        self.run(f'cmake --build "{host_dir}" --target dictbuilder -j {jobs}')
        dictbuilder = os.path.join(host_dir, "tools", "dictbuilder")
        if not os.path.isfile(dictbuilder):
            raise ConanInvalidConfiguration("host dictbuilder was not built")
        dict_dat = os.path.join(source_dir, "data", "dict_pinyin.dat")
        self.run(
            f'"{dictbuilder}" '
            f'"{os.path.join(source_dir, "data", "rawdict_utf16_65105_freq.txt")}" '
            f'"{os.path.join(source_dir, "data", "valid_utf16.txt")}" '
            f'"{dict_dat}"'
        )
        if not os.path.isfile(dict_dat) or os.path.getsize(dict_dat) == 0:
            raise ConanInvalidConfiguration("dict_pinyin.dat was not generated")

    def build(self):
        apply_conandata_patches(self)
        self._build_host_dictionary()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.includedirs = [os.path.join("include", "googlepinyin")]
        self.cpp_info.libs = ["googlepinyin"]
        self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.resdirs = [os.path.join("lib", "googlepinyin", "data")]
