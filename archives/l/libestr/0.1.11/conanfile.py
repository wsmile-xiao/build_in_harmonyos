#!/usr/bin/env python3
"""Conan recipe for libestr 0.1.11 — Autotools project (autoreconf + configure + make).

libestr is a lightweight C string library used primarily by rsyslog.
GitHub tarball does not ship configure, so autoreconf -fiv is required.
System automake already provides OHOS-aware config.guess/config.sub.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibestrConan(ConanFile):
    name = "libestr"
    version = "0.1.11"
    description = "Some essentials for string handling - a lightweight C string library used primarily by rsyslog"
    license = "LGPL-2.1"
    homepage = "https://github.com/rsyslog/libestr"
    url = "https://github.com/rsyslog/libestr"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # 本地构建注入（PR #4774 原配方缺此项——CI 红的根因之一）
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

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
        # OHOS 交叉编译：指定 build/host triplet 避免依赖 config.guess
        if self.settings.os == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-ohos",
            ])
        tc.generate()

    def build(self):
        # HMDFS workaround: set umask 022 so files are readable by other processes
        # (CMake test_package, CI workers, etc.) — default umask may create 640 files
        if self.settings.os in ("Linux", "OHOS"):
            os.umask(0o022)
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # GitHub tarball does not ship configure; bootstrap with autoreconf
        autotools.autoreconf()
        # E046 HMDFS workaround: config.status uses 'umask 077' which creates
        # temp dirs with permissions that the process cannot write to on HMDFS.
        # Remove 'umask 077' from the generated configure template so that
        # config.status temp dirs get default (writable) permissions.
        if self.settings.os in ("Linux", "OHOS"):
            conf = os.path.join(self.source_folder, "configure")
            self.run(f"sed -i 's/umask 077 && mktemp/umask 000 && mktemp/g' {conf}")
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # HMDFS workaround: ensure installed files are world-readable
        # so test_package and CI workers can access them
        if self.settings.os in ("Linux", "OHOS"):
            self.run(f"chmod -R a+r {self.package_folder}")
            self.run(f"find {self.package_folder} -type d -exec chmod a+rx {{}} \\;")

    def package_info(self):
        self.cpp_info.libs = ["libestr"]
