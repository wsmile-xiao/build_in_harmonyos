#!/usr/bin/env python3
"""Conan recipe for TAP-plugins 1.0.0, a collection of LADSPA modules."""

import glob
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class TapPluginsConan(ConanFile):
    name = "tap-plugins"
    version = "1.0.0"
    description = "Tom's Audio Processing LADSPA plug-in collection"
    license = "GPL-2.0-or-later"
    homepage = "https://tomscii.sig7.se/tap-plugins/"
    url = "https://git.hq.sig7.se/tap-plugins.git"
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tap-plugins supports Linux and OHOS, not {self.settings.os}"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "tap-plugins for HarmonyOS PC requires armv8"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        source = self.conan_data["sources"][self.version]
        get(
            self,
            url=source["url"],
            sha256=source["sha256"],
            strip_root=True,
        )

    def build(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = executables.get("c", "cc")
        cflags = "-I. -O3 -Wall -fomit-frame-pointer -funroll-loops " \
                 "-ffast-math -fPIC -DPIC -c"
        ldflags = "-nostartfiles -shared -Wl,-Bsymbolic -lc -lm"
        self.run(
            "make -j1 "
            f"CC={shlex.quote(cc)} "
            f"CFLAGS={shlex.quote(cflags)} "
            f"LDFLAGS={shlex.quote(ldflags)}",
            cwd=self.source_folder,
        )

        modules = sorted(glob.glob(os.path.join(self.source_folder, "tap_*.so")))
        if len(modules) != 19:
            raise ConanInvalidConfiguration(
                f"Expected 19 TAP LADSPA modules, built {len(modules)}"
            )
        # R51: the pinned 1.0.0 tree contains no tests/test directory and the
        # upstream Makefile has no check or test target.  The complete evidence
        # and replacement consumer coverage are recorded in MANIFEST.yml.

    def package(self):
        copy(
            self,
            "tap_*.so",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "lib", "ladspa"),
            keep_path=False,
        )
        copy(
            self,
            "ladspa.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
            keep_path=False,
        )
        copy(
            self,
            "*.rdf",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "ladspa", "rdf"),
            keep_path=False,
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "tap-plugins")
        self.cpp_info.set_property(
            "cmake_target_name", "tap-plugins::tap-plugins"
        )
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["share"]
        self.runenv_info.prepend_path(
            "LADSPA_PATH", os.path.join(self.package_folder, "lib", "ladspa")
        )
