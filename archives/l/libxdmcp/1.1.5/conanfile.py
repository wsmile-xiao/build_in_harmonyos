#!/usr/bin/env python3
"""Conan recipe for libXdmcp 1.1.5.

X.Org XDMCP (X Display Manager Control Protocol) library — encodes/decodes
the UDP packets used to discover and connect to XDM servers.
Pure autotools library; the X.Org release tarball ships pre-generated
configure + Makefile.in so no automake is needed at build time.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibxdmcpConan(ConanFile):
    name = "libxdmcp"
    version = "1.1.5"
    description = "X.Org X Display Manager Control Protocol library"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxdmcp"
    url = "https://gitlab.freedesktop.org/xorg/lib/libxdmcp"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libxdmcp supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # Xdmcp.h transitively pulls in <X11/Xfuncproto.h> from xorgproto.
        self.requires("xorgproto/2025.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # No autoreconf — X.Org release tarball ships pre-generated configure.
        tc = AutotoolsToolchain(self)
        # config.guess from 2018 cannot recognise HarmonyOS; supply the triplet
        # only for OHOS. On Linux, let config.guess detect the native triplet
        # (hardcoding aarch64 breaks x86_64 CI / developer hosts).
        if str(self.settings.os) == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # Skip upstream's tests/ subdir (which calls fork()/waitpid() and
        # the XDM auth self-test).
        tc.configure_args.append("--disable-docs")
        tc.configure_args.append("--without-xmlto")
        tc.configure_args.append("--without-fop")
        tc.configure_args.append("--without-xsltproc")
        # libxdmcp's configure ships a --enable-xdm-auth switch that pulls
        # in crypt(3); disable to avoid glibc dependency.
        tc.configure_args.append("--disable-xdm-auth")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        tc.generate()

    def build(self):
        configure_path = os.path.join(self.source_folder, "configure")
        if str(self.settings.os) == "OHOS" and os.path.exists(configure_path):
            # E002/HMDFS: autoconf temp dirs with umask 077 fail on OHOS
            # because config.status cannot execute subs1.awk inside them.
            replace_in_file(self, configure_path, "umask 077", "umask 022", strict=False)
            # /bin/bash does not exist on HarmonyOS — replace shebang with the
            # full path to the bash shipped under /data/service/hnp/bin/.
            for pattern in ("#! /bin/sh", "#!/bin/sh", "#! /bin/bash", "#!/bin/bash"):
                replace_in_file(
                    self,
                    configure_path,
                    pattern,
                    "#!/data/service/hnp/bin/bash",
                    strict=False,
                )
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # ── 上游官方测试 ──
        # libXdmcp's `test/` SUBDIRS contains a single Automake
        # check_PROGRAM: `Array`, declared in upstream test/Makefile.am
        # as `check_PROGRAMS = Array` / `TESTS = $(check_PROGRAMS)`.
        # `--enable-unit-tests` is **on by default** in upstream
        # configure (XORG_ENABLE_UNIT_TESTS([yes])), so no extra
        # configure arg is needed. Array.c exercises XdmcpAllocARRAY8/
        # ARRAY16/ARRAY32/ARRAYofARRAY8 oversize allocation rejection
        # and zero-fill semantics — 2 functions, 18+ assert calls.
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # R26 N/A — libxdmcp is not a system-name lib; keep .so for shared builds.
        self._patch_libtool_libdir()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def _patch_libtool_libdir(self):
        import re

        lib_dir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(lib_dir):
            return
        for entry in os.listdir(lib_dir):
            if not entry.endswith(".la"):
                continue
            la_path = os.path.join(lib_dir, entry)
            with open(la_path, "r", encoding="utf-8") as handle:
                content = handle.read()
            new_content = re.sub(
                r"^libdir='.*'$",
                f"libdir='{lib_dir}'",
                content,
                flags=re.MULTILINE,
            )
            if new_content != content:
                with open(la_path, "w", encoding="utf-8") as handle:
                    handle.write(new_content)

    def package_info(self):
        self.cpp_info.libs = ["Xdmcp"]
        self.cpp_info.set_property("cmake_file_name", "libxdmcp")
        self.cpp_info.set_property("cmake_target_name", "libxdmcp::libxdmcp")
    def package_info(self):
        self.cpp_info.libs = ["Xdmcp"]
        self.cpp_info.requires = ["xorgproto::xorgproto"]
        self.cpp_info.set_property("cmake_file_name", "libxdmcp")
        self.cpp_info.set_property("cmake_target_name", "libxdmcp::libxdmcp")
        self.cpp_info.set_property("pkg_config_name", "xdmcp")