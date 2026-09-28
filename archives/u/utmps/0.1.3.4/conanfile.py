#!/usr/bin/env python3
"""Conan recipe for utmps 0.1.3.4 on HarmonyOS PC."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class UtmpsConan(ConanFile):
    name = "utmps"
    version = "0.1.3.4"
    description = ("A rewrite of the wtmp/utmp system, providing a client library "
                   "and daemons that own the utmp/wtmp files")
    license = "ISC"
    homepage = "https://skarnet.org/software/utmps/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "utmps is a Unix utmp/wtmp replacement")

    def requirements(self):
        # package/deps-build lists only skalibs as unconditional; nsss is pulled
        # in solely by --enable-nsss, which we do not pass.
        # utmps/utmps.h includes <skalibs/tai.h> and every timed entry point takes
        # tain arguments, so skalibs is part of utmps' public interface: consumers
        # must inherit its headers and libs, hence transitive_* are both true.
        self.requires("skalibs/2.15.1.0", transitive_headers=True, transitive_libs=True)

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # skarnet's configure is not autotools: it takes no --host/--build and does
        # not read CFLAGS from a generated config.status, so no AutotoolsToolchain
        # here. The compiler comes from the conanbuild env (profile + VirtualBuildEnv).
        skalibs = self.dependencies["skalibs"]
        cmd = " ".join([
            "./configure",
            "--prefix=%s" % self.package_folder,
            "--with-sysdeps=%s" % os.path.join(skalibs.package_folder, "lib",
                                               "skalibs", "sysdeps"),
            "--with-include=%s" % os.path.join(skalibs.package_folder, "include"),
            "--with-lib=%s" % os.path.join(skalibs.package_folder, "lib"),
            "--enable-shared" if self.options.shared else "--disable-shared",
        ])
        self.run(cmd, cwd=self.source_folder, env="conanbuild")
        # -j1: skarnet's generated makefiles order source objects by hand.
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")
        # The upstream test entry point is run for real, not skipped: 'tests'
        # depends on $(TEST_BINS), which package/targets.mak never defines, and
        # src/tests/ is absent from the tarball, so the check loop iterates over
        # zero cases. That is the evidence for N_static = 0.
        self.run("make -j1 check", cwd=self.source_folder, env="conanbuild")
        self.run("make -j1 install", cwd=self.source_folder, env="conanbuild")

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "utmps")
        self.cpp_info.libs = ["utmps"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
