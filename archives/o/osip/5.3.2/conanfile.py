#!/usr/bin/env python3
"""Conan recipe for GNU oSIP (libosip2) 5.3.2 on OHOS aarch64.

oSIP is the GNU SIP (RFC 3261) parsing library. It builds two libraries:
libosip2 (transaction/statemachine) and libosipparser2 (SIP message parser).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OsipConan(ConanFile):
    name = "osip"
    version = "5.3.2"
    description = "GNU oSIP - an implementation of the SIP (RFC 3261) protocol"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.gnu.org/software/osip/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # AutotoolsToolchain does not inject OHOS build/host triplets, and the
        # upstream config.guess (2014) cannot guess the HarmonyOS host. The
        # linux-ohos triplet works together with 0002/0003 config.guess/sub
        # patches (same pattern as aalib 1.4p5).
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-ohos",
        ])
        # Build the upstream torture test tools in src/test (noinst_PROGRAMS
        # behind the COMPILE_TESTS conditional, default off).
        tc.configure_args.append("--enable-test")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream has no TESTS registration (make check is a no-op), but the
        # torture tools built above come with real SIP message corpora: run
        # them here so the upstream test assets execute for real.
        autotools.make(target="check")
        res_dir = os.path.join(self.source_folder, "src", "test", "res")
        test_dir = os.path.join(self.build_folder, "src", "test")
        for dataset in ("torture_hgs", "torture_msgs2"):
            self.run(f"./torture_test {res_dir}/{dataset}", cwd=test_dir)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["osip2", "osipparser2"]
