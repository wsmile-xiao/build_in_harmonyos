#!/usr/bin/env python3
"""Conan recipe for libgetline 1.0 (upstream: github.com/hilderingt/libgetline).

A tiny autotools/libtool C library that reads a file one line at a time.

OHOS adaptations:
  - configure temp dir: umask 077 -> umask 022 (patches/0001, E011/E129 — HMDFS
    forces the setgid bit, so a umask-077 directory becomes drwx--S--- and is
    not writable even by its owner, breaking config.status).
  - build triplet: upstream config.guess cannot identify HarmonyOS
    (uname -s = "HarmonyOS"); both it and the bundled config.sub predate the
    platform, so autotools is told the accepted generic triplet
    aarch64-unknown-linux-gnu (same pattern as archives/a a52dec/abiword-*).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibgetlineConan(ConanFile):
    name = "libgetline"
    version = "1.0"
    description = "Read a file each a line (file line reader library)"
    license = "GPL-3.0"
    homepage = "https://github.com/hilderingt/libgetline"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libgetline supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        # src/libgetline.c uses `#include "libgetlineP.h"` (header lives in
        # include/), which conan's out-of-tree (build-release) layout cannot
        # resolve through automake's default -I flags; the include dir is
        # injected via CPPFLAGS inside build() (see below).
        if str(self.settings.os) == "OHOS":
            # config.guess/config.sub cannot recognize HarmonyOS uname output.
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        env = Environment()
        env.append(
            "CPPFLAGS",
            f"-I{os.path.join(self.source_folder, 'include')}",
            separator=" ",
        )
        with env.vars(self).apply():
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])
            # Upstream has no tests (Makefile.am declares no TESTS/check_PROGRAMS);
            # the automake default check target is an empty no-op run for evidence.
            autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["getline"]
        self.cpp_info.set_property("cmake_file_name", "libgetline")
        self.cpp_info.set_property("cmake_target_name", "libgetline::libgetline")
        self.cpp_info.set_property("pkg_config_name", "libgetline")