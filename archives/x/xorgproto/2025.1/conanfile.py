#!/usr/bin/env python3
"""Conan recipe for xorgproto 2025.1."""

import os
import sys
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get


PC_MODULES = (
    "applewmproto",
    "bigreqsproto",
    "compositeproto",
    "damageproto",
    "dmxproto",
    "dpmsproto",
    "dri2proto",
    "dri3proto",
    "fixesproto",
    "fontsproto",
    "glproto",
    "inputproto",
    "kbproto",
    "presentproto",
    "randrproto",
    "recordproto",
    "renderproto",
    "resourceproto",
    "scrnsaverproto",
    "videoproto",
    "xcmiscproto",
    "xextproto",
    "xf86bigfontproto",
    "xf86dgaproto",
    "xf86driproto",
    "xf86vidmodeproto",
    "xineramaproto",
    "xproto",
    "xwaylandproto",
)

DOCS = (
    "compositeproto.txt",
    "damageproto.txt",
    "dri2proto.txt",
    "dri3proto.txt",
    "fixesproto.txt",
    "presentproto.txt",
    "randrproto.txt",
    "renderproto.txt",
    "resproto.txt",
    "xv-protocol-v2.txt",
    "xwaylandproto.txt",
)


class XorgprotoConan(ConanFile):
    name = "xorgproto"
    version = "2025.1"
    description = "X Window System protocol headers"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/proto/xorgproto"
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xorgproto supports Linux and OHOS, not {self.settings.os}"
            )

    def package_id(self):
        self.info.settings.rm_safe("build_type")

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )

    def build(self):
        script = os.path.join(self.source_folder, "scripts", "keysym-generator.py")
        header = os.path.join(self.source_folder, "include", "X11", "XF86keysym.h")
        result = self.run(
            f'"{sys.executable}" "{script}" -v --header "{header}" verify',
            ignore_errors=True,
            env=None,
        )
        if result == 77:
            self.output.warning(
                "upstream evdev-keysym-check skipped because python-libevdev is absent"
            )
        elif result != 0:
            raise ConanException(f"upstream evdev-keysym-check failed with {result}")

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = compiler_executables.get("c")
        if not compiler:
            raise ConanException(
                "tools.build:compiler_executables must define the C compiler"
            )
        fd_set_member = self._detect_fd_set_member(compiler)
        template = Path(
            self.source_folder, "include", "X11", "Xpoll.h.in"
        ).read_text(encoding="utf-8")
        if template.count("@USE_FDS_BITS@") != 1:
            raise ConanException("Xpoll.h.in must contain one fd_set placeholder")
        output = Path(self.build_folder, "include", "X11", "Xpoll.h")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            template.replace("@USE_FDS_BITS@", fd_set_member), encoding="utf-8"
        )
        self.output.info(f"generated Xpoll.h with fd_set.{fd_set_member}")

    def package(self):
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        generated_header = Path(self.build_folder, "include", "X11", "Xpoll.h")
        if not generated_header.is_file():
            raise ConanException("build() did not generate X11/Xpoll.h")
        copy(
            self,
            "Xpoll.h",
            src=str(generated_header.parent),
            dst=os.path.join(self.package_folder, "include", "X11"),
        )
        copy(
            self,
            "COPYING-*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        doc_dir = Path(self.package_folder) / "share" / "doc" / "xorgproto"
        doc_dir.mkdir(parents=True, exist_ok=True)
        for filename in DOCS:
            source = Path(self.source_folder) / filename
            (doc_dir / filename).write_bytes(source.read_bytes())

        pc_dir = Path(self.package_folder) / "share" / "pkgconfig"
        pc_dir.mkdir(parents=True, exist_ok=True)
        for module in PC_MODULES:
            template = Path(self.source_folder, f"{module}.pc.in").read_text(
                encoding="utf-8"
            )
            content = template.replace("@prefix@", "${pcfiledir}/../..")
            content = content.replace("@includedir@", "${prefix}/include")
            (pc_dir / f"{module}.pc").write_text(content, encoding="utf-8")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "xorgproto")
        self.cpp_info.set_property("cmake_target_name", "xorgproto::xorgproto")
        pc_dir = os.path.join(self.package_folder, "share", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

    def _detect_fd_set_member(self, compiler):
        probe_dir = Path(self.build_folder, "fd-set-probe")
        probe_dir.mkdir(parents=True, exist_ok=True)
        includes = """#include <sys/param.h>
#include <sys/types.h>
#include <sys/time.h>
#include <sys/select.h>
"""
        for member in ("fds_bits", "__fds_bits"):
            source = probe_dir / f"{member}.c"
            output = probe_dir / f"{member}.o"
            source.write_text(
                f"{includes}int main(void) {{ fd_set value; "
                f"(void)value.{member}; return 0; }}\n",
                encoding="utf-8",
            )
            result = self.run(
                f'"{compiler}" -Werror -c "{source}" -o "{output}"',
                ignore_errors=True,
                env=None,
            )
            if result == 0:
                return member
        raise ConanException(
            "target fd_set exposes neither fds_bits nor __fds_bits"
        )
