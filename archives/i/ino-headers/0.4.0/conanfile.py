#!/usr/bin/env python3
"""Conan recipe — ino-headers 0.4.0 (header-only C API for NASPRO ino).

ino-headers ships the public API headers of the ino JavaScript-execution
architecture: a single header (lib.h) plus a pkg-config template
(ino-headers-0.pc.in). There is nothing to compile — upstream `make all`
and `make check` are both no-ops, and the header contains declarations
only (implementations live in the downstream ino backend libraries).
The recipe therefore skips the upstream autotools flow entirely (no
configure/mktemp landmines on OHOS — same hand-install approach as the
published kicad-demos 10.0.4 archive) and installs the header directly
in package():

    include/ino-0/ino/lib.h        (upstream: inoincludedir = ${includedir}/ino-0/ino)
    lib/pkgconfig/ino-headers-0.pc (upstream .pc.in expansion, relocatable prefix)
    licenses/COPYING               (ISC)

Consumers include <ino/lib.h> with -I<prefix>/include/ino-0 (see the
pkg-config Cflags and cpp_info.includedirs below). R38: header-only
package — no commands.json needed (no executables).
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get, save
from conan.tools.layout import basic_layout


class InoHeadersConan(ConanFile):
    name = "ino-headers"
    version = "0.4.0"
    description = ("Common headers for all ino (JavaScript execution) "
                   "implementations")
    license = "ISC"
    homepage = "https://naspro.sourceforge.net/libraries/ino/"
    url = "https://naspro.sourceforge.net/libraries/ino/"
    topics = ("javascript", "embedding", "header-only", "naspro")

    package_type = "header-library"

    # 无编译产物，保留 settings 满足 CI L0 门禁的显式 settings 声明要求
    # （kicad-demos / linux-firmware-brcm 先例同款）。
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R32: recipe supports Linux and OHOS targets only
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ino-headers does not support os={self.settings.os}")
        # 防漂移校验（kicad-demos 先例同款）：发布包内容固定，逐一断言
        # 打包所需的源文件在位。无任何编译动作。
        for rel in ("lib.h", "COPYING", "Makefile.am", "configure.ac",
                    "ino-headers-0.pc.in", "README", "NEWS", "ChangeLog"):
            if not os.path.isfile(os.path.join(self.source_folder, rel)):
                raise ConanException(f"source drift: {rel} missing")
        self.output.info("header-only package: nothing to compile "
                         "(source layout verified)")

    def package(self):
        # Upstream Makefile.am installs lib.h to ${includedir}/ino-0/ino
        # (inoincludedir) — mirror that layout (kicad-demos hand-install
        # paradigm; no configure on OHOS needed).
        copy(self, "lib.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include", "ino-0", "ino"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Generate the pkg-config file (upstream ships only the .pc.in
        # template). Relocatable ${pcfiledir} prefix keeps the pc file
        # usable after the package folder is moved (OHOS deploy).
        pc_content = (
            "prefix=${{pcfiledir}}/../..\n"
            "exec_prefix=${{prefix}}\n"
            "includedir=${{prefix}}/include\n\n"
            "Name: ino headers\n"
            "Description: Common headers for all ino implementations\n"
            "URL: https://naspro.sourceforge.net/libraries/ino/\n"
            "Version: {ver}\n"
            "Libs:\n"
            "Cflags: -I${{includedir}}/ino-0\n"
        ).format(ver=self.version)
        save(self, os.path.join(self.package_folder, "lib", "pkgconfig",
                                "ino-headers-0.pc"), pc_content)

    def package_id(self):
        # 纯头文件包：内容与 settings 无关，清空 package id
        # （kicad-demos / mypaint-brushes 复验版先例同款）。
        self.info.clear()

    def package_info(self):
        # Header-only: no libs, no binaries.
        self.cpp_info.set_property("cmake_file_name", "ino-headers")
        self.cpp_info.set_property("cmake_target_name", "ino-headers::ino-headers")
        self.cpp_info.set_property("pkg_config_name", "ino-headers-0")
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        # Public include root is include/ino-0 so that <ino/lib.h> resolves
        # (upstream pc Cflags: -I${includedir}/ino-0).
        self.cpp_info.includedirs = ["include/ino-0"]
        # Expose the installed pc file for pkg-config consumers.
        self.buildenv_info.append_path(
            "PKG_CONFIG_PATH",
            os.path.join(self.package_folder, "lib", "pkgconfig"))
