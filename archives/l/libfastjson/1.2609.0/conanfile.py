#!/usr/bin/env python3
"""Conan recipe for libfastjson 1.2609.0 — Autotools project (configure + make).

libfastjson is a fast JSON parser/generator library from the rsyslog project.
Official release tarball ships configure; patches 0001/0002 add HarmonyOS
(OHOS) platform recognition to config.guess/config.sub.

Upstream test suite (make check, 22 registered targets in tests/Makefile.am)
runs inside build() per L1 policy.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibfastjsonConan(ConanFile):
    name = "libfastjson"
    version = "1.2609.0"
    description = "A fast JSON parser/generator library from the rsyslog project, fork of json-c with performance improvements"
    license = "MIT"
    homepage = "https://github.com/rsyslog/libfastjson"
    url = "https://github.com/rsyslog/libfastjson"

    package_type = "library"
    implements = ["auto_shared_fpic"]

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # libfastjson has no external dependencies

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: no system-name conflict, default static build
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # OHOS cross compile: explicit build/host triplets
        # (config.guess/sub patched for HarmonyOS by 0001/0002)
        if self.settings.os == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-ohos",
            ])
        tc.generate()

    def build(self):
        # HMDFS workaround: umask 022 so generated files are world-readable
        if self.settings.os in ("Linux", "OHOS"):
            os.umask(0o022)
        apply_conandata_patches(self)
        # E046 HMDFS workaround: config.status uses 'umask 077' which creates
        # temp files (confXXXX/subs1.awk) that the process cannot write to on
        # HMDFS. Remove 'umask 077' from the generated configure script so
        # config.status temp files get default (writable) permissions.
        if self.settings.os in ("Linux", "OHOS"):
            conf = os.path.join(self.source_folder, "configure")
            self.run(f"sed -i 's/umask 077 && mktemp/umask 000 && mktemp/g' {conf}")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # L1: run upstream official test suite (make check).
        # 22 registered targets in tests/Makefile.am:
        # 21 .test drivers (test1/test2/test4/... with formatted variants)
        # + chk_version. Fails the build if any test fails.
        # Note: test_dump_buffered's file-write path is skipped via runtime
        # feature detection (0003) when tmpfile() is unavailable (OHOS /tmp
        # read-only); its in-memory checks still run.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # HMDFS workaround: ensure installed files are world-readable
        if self.settings.os in ("Linux", "OHOS"):
            self.run(f"chmod -R a+r {self.package_folder}")
            self.run(f"find {self.package_folder} -type d -exec chmod a+rx {{}} \\;")

    def package_info(self):
        self.cpp_info.libs = ["libfastjson"]
