#!/usr/bin/env python3
"""Conan recipe for xcb-util-renderutil 0.3.10.

XCB Render extension utility library — provides convenience functions
for the XCB RENDER extension (picture formats, glyphs, cached
pictformats). Pure autotools; the official X.Org release tarball ships
pre-generated configure + Makefile.in so no automake is needed.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, load, replace_in_file, save, export_conandata_patches, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class XcbUtilRenderutilConan(ConanFile):
    name = "xcb-util-renderutil"
    version = "0.3.10"
    description = "XCB RENDER-extension utilities library"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxcb-render-util"
    url = "https://gitlab.freedesktop.org/xorg/lib/libxcb-render-util"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    generators = "PkgConfigDeps"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xcb-util-renderutil supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("libxcb/1.17.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # config.guess from 2018 cannot recognise HarmonyOS; supply the triplet.
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        tc.generate()

        # ── Patch conan-generated pkg-config files for configure checks ──
        conan_pc_dir = os.path.join(self.build_folder, "conan")
        libxcb_pkg = self.dependencies["libxcb"].package_folder

        # 1) xcb-util-renderutil's configure checks:
        #   pkg-config --variable=xcbproto_version xcb
        # The Conan-generated xcb.pc does not include this custom variable
        # (it's upstream-specific, set from @XCBPROTO_VERSION@ in xcb.pc.in).
        conan_xcb_pc = os.path.join(conan_pc_dir, "xcb.pc")
        if os.path.isfile(conan_xcb_pc):
            existing = load(self, conan_xcb_pc)
            if "xcbproto_version" not in existing:
                # libxcb/1.17.0 was built against xcb-proto/1.17.0
                patched = existing + "\nxcbproto_version=1.17.0\n"
                save(self, conan_xcb_pc, patched)

        # 2) configure also does PKG_CHECK_MODULES(XCB_RENDER, xcb-render)
        # The libxcb Conan package ships libxcb-render.so but does not
        # generate a xcb-render.pc (only xcb.pc). Create one so the
        # pkg-config check passes.
        conan_xcb_render_pc = os.path.join(conan_pc_dir, "xcb-render.pc")
        if not os.path.isfile(conan_xcb_render_pc):
            xcb_render_pc_content = (
                f"prefix={libxcb_pkg}\n"
                "exec_prefix=${prefix}\n"
                "libdir=${prefix}/lib\n"
                "includedir=${prefix}/include\n"
                "\n"
                "Name: XCB Render\n"
                "Description: X C Binding RENDER extension\n"
                "Version: 1.17.0\n"
                "Requires: xcb\n"
                'Libs: -L"${libdir}" -lxcb-render\n'
                'Cflags: -I"${includedir}"\n'
            )
            save(self, conan_xcb_render_pc, xcb_render_pc_content)

        # 3) Remove broken libtool .la files from the libxcb dependency.
        # Conan-generated .la files reference absolute paths to other
        # package .la files (libXau.la, libXdmcp.la) that may not exist
        # in the current Conan layout. Since we build shared libraries,
        # removing .la files lets libtool fall back to -l flags from
        # pkg-config, which works correctly.
        libxcb_lib_dir = os.path.join(libxcb_pkg, "lib")
        if os.path.isdir(libxcb_lib_dir):
            for la_name in os.listdir(libxcb_lib_dir):
                if la_name.endswith(".la"):
                    la_path = os.path.join(libxcb_lib_dir, la_name)
                    if os.path.isfile(la_path):
                        os.remove(la_path)

    def build(self):
        apply_conandata_patches(self)
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

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["xcb-render-util"]
        self.cpp_info.set_property("cmake_file_name", "xcb-util-renderutil")
        self.cpp_info.set_property("cmake_target_name", "xcb-util-renderutil::xcb-util-renderutil")
        self.cpp_info.set_property("pkg_config_name", "xcb-renderutil")
