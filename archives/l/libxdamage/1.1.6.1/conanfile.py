#!/usr/bin/env python3
"""Conan recipe for libXdamage 1.1.6.1.

X.Org libXdamage — client library for the DAMAGE extension (tracking of
modified screen regions by the X server).  Pure autotools; the official
X.Org release tarball ships a pre-generated configure + Makefile.in, so no
autoreconf/automake run is needed at build time.

OHOS adaptation (patches declared in conandata.yml):
  - config.guess: *:HarmonyOS:* branch emitting aarch64-unknown-linux-ohos
                  (E007 — upstream config.guess 2021-06-03 cannot detect
                  HarmonyOS; using --build/--host instead is forbidden)
  - config.sub:   ohos-linux triplet + ohos* OS list + linux-ohos* kernel/OS
                  validation (E007)
  - configure:    umask 077 -> 022 so config.status can execute subs1.awk
                  inside its temp dir on HMDFS (E002)
"""

import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibxdamageConan(ConanFile):
    name = "libxdamage"
    version = "1.1.6.1"
    description = "X.Org libXdamage — client library for the DAMAGE extension"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxdamage"
    url = "https://gitlab.freedesktop.org/xorg/lib/libxdamage"
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
    exports_sources = "conandata.yml", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libxdamage supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # Xdamage.h includes <X11/extensions/damagewire.h> and
        # <X11/Xfuncproto.h> (xorgproto), <X11/extensions/Xfixes.h>
        # (libxfixes) and <X11/Xlib.h> (libx11); configure's
        # PKG_CHECK_MODULES needs damageproto/xfixes/fixesproto/xextproto/
        # x11/xproto, and XDamageSubtract's XserverRegion (Region) comes from
        # Xfixes.h so libXfixes must also be linked.
        # Dep chain aligned with the cmd-pkgs track (same as main's merged
        # libxdamage/1.1.6.1): libx11/6.4.0 + libxext/6.4.0 + libxfixes/6.1.0 +
        # xorgproto/2025.1.
        self.requires("xorgproto/2025.1", transitive_headers=True)
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxfixes/6.1.0", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        # No autoreconf — the X.Org release tarball ships configure already.
        tc = AutotoolsToolchain(self)
        # config.guess/config.sub are patched for HarmonyOS (E007), so native
        # detection works: do NOT pass --build/--host (forbidden by E007,
        # it would make configure believe it cross-compiles).
        # libXdamage 1.1.6.1 has no docs/xmlto/fop/xsltproc knobs in configure.
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._fix_dep_la_files()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # ── 上游官方测试 ──
        # libXdamage 1.1.6.1 ships NO check_PROGRAMS / TESTS: `make check`
        # recurses into src/ and reports "Nothing to be done".
        # We still run it so any future upstream test is picked up and so
        # the recipe never silently skips the upstream test entry point.
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
        """Point installed .la files at the final package lib dir."""
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

    def _fix_dep_la_files(self):
        """Drop stale .la references from dependency .la files.

        libtool .la files record absolute paths to other .la files (e.g.
        libXfixes.la -> libX11.la -> /conan2/p/<build-folder>/p/lib/libX11.la).
        Those build folders are removed after the dependency's `conan create`,
        so linking libXdamage fails with "is not a valid libtool archive".
        Only references to files that no longer exist are removed.
        """
        for dep in self.dependencies.values():
            dep_lib = os.path.join(dep.package_folder or "", "lib")
            if not os.path.isdir(dep_lib):
                continue
            for entry in os.listdir(dep_lib):
                if not entry.endswith(".la"):
                    continue
                la_path = os.path.join(dep_lib, entry)
                with open(la_path, "r", encoding="utf-8") as handle:
                    content = handle.read()
                new_content = content
                for match in re.finditer(r"(\S+\.la)", content):
                    la_ref = match.group(1)
                    if not os.path.isfile(la_ref):
                        new_content = new_content.replace(la_ref, "")
                new_content = re.sub(r"  +", " ", new_content)
                if new_content != content:
                    with open(la_path, "w", encoding="utf-8") as handle:
                        handle.write(new_content)

    def package_info(self):
        self.cpp_info.libs = ["Xdamage"]
        self.cpp_info.requires = [
            "xorgproto::xorgproto",
            "libx11::libx11",
            "libxext::libxext",
            "libxfixes::libxfixes",
        ]
        self.cpp_info.set_property("cmake_file_name", "libxdamage")
        self.cpp_info.set_property("cmake_target_name", "libxdamage::libxdamage")
        self.cpp_info.set_property("pkg_config_name", "xdamage")
