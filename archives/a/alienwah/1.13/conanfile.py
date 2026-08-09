#!/usr/bin/env python3
"""Conan recipe for AlienWah 1.13."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AlienwahConan(ConanFile):
    name = "alienwah"
    version = "1.13"
    description = "Alien-wah LADSPA audio effect plugin"
    license = "GPL-2.0-or-later AND LGPL-2.1-or-later"
    homepage = "http://plugin.org.uk/releases/alienwah/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} is not supported")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(
            self,
            **self.conan_data["ladspa_sdk"],
            destination=os.path.join(self.source_folder, "_ladspa_sdk"),
            strip_root=True,
        )
        apply_conandata_patches(self)

    def generate(self):
        VirtualBuildEnv(self).generate()

    @staticmethod
    def _quote(value):
        return shlex.quote(str(value).replace("\\", "/"))

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("cpp", "clang++")

    def _dependency_includes(self):
        return [f"-I{os.path.join(self.source_folder, '_ladspa_sdk', 'src')}"]

    def _conf_list(self, name):
        return [str(value) for value in self.conf.get(name, default=[], check_type=list)]

    def build(self):
        os.makedirs(self.build_folder, exist_ok=True)
        cxx = self._compiler()
        source = os.path.join(self.source_folder, "aw.cpp")
        obj = os.path.join(self.build_folder, "aw.o")
        plugin = os.path.join(self.build_folder, "aw.so")
        cxxflags = (
            ["-fPIC", "-O2", "-Wall"]
            + self._dependency_includes()
            + self._conf_list("tools.build:cxxflags")
        )
        shared_flags = self._conf_list("tools.build:sharedlinkflags")
        self.run(
            f"{self._quote(cxx)} "
            f"{' '.join(self._quote(flag) for flag in cxxflags)} "
            f"-c {self._quote(source)} -o {self._quote(obj)}",
            env="conanbuild",
        )
        self.run(
            f"{self._quote(cxx)} -shared {self._quote(obj)} "
            f"{' '.join(self._quote(flag) for flag in shared_flags)} "
            f"-lm -o {self._quote(plugin)}",
            env="conanbuild",
        )

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(
            self,
            "COPYING",
            os.path.join(self.source_folder, "_ladspa_sdk"),
            os.path.join(self.package_folder, "licenses", "ladspa"),
            keep_path=False,
        )
        copy(
            self,
            "ladspa.h",
            os.path.join(self.source_folder, "_ladspa_sdk", "src"),
            os.path.join(self.package_folder, "include"),
            keep_path=False,
        )
        copy(self, "README", self.source_folder, os.path.join(self.package_folder, "share", "alienwah"), keep_path=False)
        copy(self, "aw.so", self.build_folder, os.path.join(self.package_folder, "lib", "ladspa"), keep_path=False)

    def package_info(self):
        plugin_dir = os.path.join(self.package_folder, "lib", "ladspa")
        self.cpp_info.libdirs = ["lib/ladspa"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.resdirs = ["lib/ladspa"]
        self.runenv_info.define_path("LADSPA_PATH", plugin_dir)
