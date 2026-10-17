#!/usr/bin/env python3
"""Conan recipe — spacenavd 1.3.1 (3Dconnexion space-navigator daemon).

Upstream ships a handwritten `configure` (no autoconf) that honours the
CC/CFLAGS environment and --prefix, and owns an --disable-x11 switch for
the optional X11 communication mode.  OHOS has neither X11 nor gcc, so
the recipe configures with --disable-x11, CC=<ohos clang> and
CFLAGS=-DHAVE_STDINT_H: the handwritten configure's config.h template
never probes for stdint.h, and src/proto.h's int32_t usage is normally
masked by the X11 header chain (measured: with X11 disabled, proto.h
fails on unknown type name int32_t).

The daemon needs a real space-navigator device (/dev/input/event*) for
its service loop; the consumer test therefore exercises the CLI surface
(-V/-h/invalid option) and explicitly does not start the device loop.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class SpacenavdConan(ConanFile):
    name = "spacenavd"
    version = "1.3.1"
    description = (
        "spacenavd: user-space daemon that makes 3Dconnexion "
        "space-navigator devices available through a unix socket"
    )
    license = "GPL-3.0-or-later"
    homepage = "http://spacenav.sourceforge.net"
    url = ""  # CI fills this
    topics = ("input", "daemon", "3d-mouse", "cli")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"spacenavd not validated for {self.settings.os}"
            )

    def export_sources(self):
        # No upstream patches; conandata.yml declares none.  The method is
        # kept for the G1 recipe-completeness gate.
        pass

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)  # no-op: conandata declares no patches
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = (compilers or {}).get("c") or "clang"
        src = self.source_folder
        prefix = self.package_folder
        # Handwritten configure: honours CC/CFLAGS env and writes them into
        # the Makefile.  --disable-x11: OHOS has no X11; leaving the (default
        # on) X11 mode enabled also unmasks proto.h's missing stdint.h
        # dependency, solved here with -DHAVE_STDINT_H.
        self.run(
            f'CFLAGS="-DHAVE_STDINT_H" CC="{cc}" '
            f'./configure --prefix="{prefix}" --disable-x11',
            cwd=src,
        )
        self.run(f'make -j2 CC="{cc}"', cwd=src)

    def package(self):
        src = self.source_folder
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, "spacenavd", src=src, dst=bindir, keep_path=False)
        copy(self, "README.md", src=src,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
