#!/usr/bin/env python3
"""Conan recipe for xcb-util-image 0.4.1.

XCB Image convenience library — provides image creation, manipulation,
and conversion functions on top of XCB and the SHM extension. Pure
autotools; the x.org release tarball ships pre-generated configure +
Makefile.in so no automake is needed at build time.
"""

import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load, replace_in_file, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps


class XcbUtilImageConan(ConanFile):
    name = "xcb-util-image"
    version = "0.4.1"
    description = "XCB Image convenience library (image creation, manipulation, conversion)"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxcb-image"
    url = "https://gitlab.freedesktop.org/xorg/lib/libxcb-image"
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

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xcb-util-image supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("libxcb/1.17.0")
        self.requires("xorgproto/2025.1")
        self.requires("xcb-util/0.4.1")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        tc.generate()

        # The XCB_UTIL_COMMON m4 macro queries `pkg-config --variable=xcbproto_version xcb`
        # to verify libxcb was compiled against xcb-proto >= 1.6. Conan's
        # PkgConfigDeps generates a minimal xcb.pc from cpp_info that lacks
        # this custom variable. Patch the generated xcb.pc to include it.
        conan_pc_dir = os.path.join(self.build_folder, "conan")
        xcb_pc = os.path.join(conan_pc_dir, "xcb.pc")
        if os.path.isfile(xcb_pc):
            existing = load(self, xcb_pc)
            if "xcbproto_version" not in existing:
                xcb_pkg = self.dependencies["libxcb"].package_folder
                orig_xcb_pc = os.path.join(xcb_pkg, "lib", "pkgconfig", "xcb.pc")
                if os.path.isfile(orig_xcb_pc):
                    orig_content = load(self, orig_xcb_pc)
                    for line in orig_content.splitlines():
                        if line.startswith("xcbproto_version="):
                            patch_line = line + "\n"
                            lines = existing.splitlines()
                            insert_idx = 0
                            for i, ln in enumerate(lines):
                                if ln.startswith("prefix=") or ln.startswith("exec_prefix="):
                                    insert_idx = i + 1
                            lines.insert(insert_idx, patch_line.rstrip())
                            save(self, xcb_pc, "\n".join(lines) + "\n")
                            break

        # libxcb ships extension .pc files (xcb-shm.pc, xcb-render.pc, etc.)
        # in its package's lib/pkgconfig/ directory. PkgConfigDeps only
        # generates xcb.pc from cpp_info, so the extension .pc files are
        # not in the generators directory. Copy extension .pc files to
        # the generators directory so configure finds xcb-shm.
        xcb_pkg = self.dependencies["libxcb"].package_folder
        xcb_pc_dir = os.path.join(xcb_pkg, "lib", "pkgconfig")
        conan_gen_dir = os.path.join(self.build_folder, "conan")
        if os.path.isdir(xcb_pc_dir) and os.path.isdir(conan_gen_dir):
            for pc_file in os.listdir(xcb_pc_dir):
                if pc_file == "xcb.pc":
                    continue  # don't overwrite the patched one
                src_pc = os.path.join(xcb_pc_dir, pc_file)
                dst_pc = os.path.join(conan_gen_dir, pc_file)
                if os.path.isfile(src_pc) and not os.path.isfile(dst_pc):
                    copy(self, pc_file, src=xcb_pc_dir, dst=conan_gen_dir)

    def _fix_dependency_la_files(self):
        """Fix stale build-time paths in dependency .la files."""
        for dep_name in ("libxcb", "xcb-util"):
            dep = self.dependencies[dep_name]
            dep_lib = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(dep_lib):
                continue
            for entry in os.listdir(dep_lib):
                if not entry.endswith(".la"):
                    continue
                la_path = os.path.join(dep_lib, entry)
                with open(la_path, "r", encoding="utf-8") as f:
                    content = f.read()
                content = re.sub(
                    r"^libdir='.*'$",
                    f"libdir='{dep_lib}'",
                    content,
                    flags=re.MULTILINE,
                )

                def _replace_la(m):
                    la_file = m.group(1)
                    la_base = os.path.basename(la_file)
                    lib_name = la_base[3:-3]
                    return f" -l{lib_name}"

                content = re.sub(
                    r"(\s+/[^ ]+\.la\b)",
                    _replace_la,
                    content,
                )
                with open(la_path, "w", encoding="utf-8") as f:
                    f.write(content)

    def build(self):
        self._fix_dependency_la_files()
        configure_path = os.path.join(self.source_folder, "configure")
        if str(self.settings.os) == "OHOS" and os.path.exists(configure_path):
            replace_in_file(self, configure_path, "umask 077", "umask 022", strict=False)
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
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        self._patch_libtool_libdir()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def _patch_libtool_libdir(self):
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
        self.cpp_info.libs = ["xcb-image"]
        self.cpp_info.set_property("cmake_file_name", "xcb-util-image")
        self.cpp_info.set_property("cmake_target_name", "xcb-util-image::xcb-util-image")
        self.cpp_info.set_property("pkg_config_name", "xcb-image")
