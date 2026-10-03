#!/usr/bin/env python3
"""Conan recipe for xjobs 20241010 (GNU Autotools)."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain


class XjobsConan(ConanFile):
    name = "xjobs"
    version = "20241010"
    package_type = "application"
    license = "GPL-2.0-or-later"
    homepage = "https://www.maier-komor.de/xjobs.html"
    description = "A parallel command launcher with bounded concurrency"
    topics = ("parallel", "jobs", "command-line")
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("xjobs supports Linux and OHOS")
        if str(self.settings.compiler) not in ("gcc", "clang"):
            raise ConanInvalidConfiguration("xjobs requires GCC or Clang")

    def build_requirements(self):
        self.tool_requires("flex/2.6.4")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-ohos",
                "--host=aarch64-unknown-linux-ohos",
            ])
        tc.extra_cflags = ["-fPIE"]
        tc.extra_ldflags = ["-pie", "-Wl,-z,relro,-z,now"]
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        copy(self, "xjobs", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "xjobs.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
