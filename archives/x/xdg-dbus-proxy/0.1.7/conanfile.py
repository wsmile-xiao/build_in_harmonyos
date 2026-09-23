#!/usr/bin/env python3
"""Conan recipe — xdg-dbus-proxy 0.1.7 (Meson).

xdg-dbus-proxy is a filtering proxy for D-Bus connections, used by
Flatpak to sandbox applications. It builds a single executable
(xdg-dbus-proxy) that sits between a client and the D-Bus bus daemon,
filtering messages according to a policy.

Adapted to HarmonyOS PC (aarch64). See notes.md for details.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.layout import basic_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps


class XdgDbusProxyConan(ConanFile):
    name = "xdg-dbus-proxy"
    version = "0.1.7"
    description = "Filtering proxy for D-Bus connections (Flatpak sandboxing)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/flatpak/xdg-dbus-proxy"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.88.0.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xdg-dbus-proxy {self.version} only supports Linux and OHOS, "
                f"got os={self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Pin ar/as/strip/nm/ranlib by absolute path (same pattern as glib
        # 2.88.0.1: CI worker exports llvm-* names not on PATH).
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}"
            )

        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = tools["strip"]
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        # Disable tests (needs running D-Bus daemon) and man pages (needs xsltproc).
        tc.project_options["tests"] = "false"
        tc.project_options["man"] = "disabled"
        tc.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

        self._create_gio_unix_pc()

    def _create_gio_unix_pc(self):
        """Create gio-unix-2.0.pc from gio-2.0.pc.

        Conan's PkgConfigDeps generates .pc files from cpp_info components.
        glib's recipe defines gio-2.0 but not gio-unix-2.0 (the Unix-specific
        GIO pkg-config module). meson's dependency('gio-unix-2.0') needs this
        separate .pc file.

        We create it from gio-2.0.pc with:
        - Name/Description changed to gio-unix-2.0
        - Cflags adds -I${includedir}/gio-unix-2.0 (where Unix headers live:
          gio/gunixfdmessage.h, gio/gunixconnection.h, etc.)
        """
        gens = self.generators_folder
        gio_unix_pc = os.path.join(gens, "gio-unix-2.0.pc")
        gio_pc = os.path.join(gens, "gio-2.0.pc")
        if not os.path.isfile(gio_unix_pc) and os.path.isfile(gio_pc):
            with open(gio_pc) as f:
                lines = f.readlines()
            new_lines = []
            for line in lines:
                if line.startswith("Name:"):
                    new_lines.append("Name: gio-unix-2.0\n")
                elif line.startswith("Description:"):
                    new_lines.append("Description: GIO Unix-specific APIs\n")
                elif line.startswith("Cflags:"):
                    # Add gio-unix-2.0 include path (Unix headers live there)
                    # NOTE: ${includedir} in Conan's gio-2.0.pc is
                    # ${prefix}/include/glib-2.0, not ${prefix}/include.
                    # Use ${prefix}/include/gio-unix-2.0 to reach the Unix headers.
                    rest = line[len("Cflags:"):].rstrip()
                    new_lines.append(f"Cflags: -I${{prefix}}/include/gio-unix-2.0 {rest}\n")
                else:
                    new_lines.append(line)
            with open(gio_unix_pc, "w") as f:
                f.writelines(new_lines)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        if cross_building(self):
            self.output.info(
                "cross-building: skip meson.test() "
                "(OHOS binaries are not runnable on the build host)"
            )
        else:
            if hasattr(os, "uname") and os.uname().sysname in ("OHOS", "HarmonyOS"):
                build_folder = self.build_folder

                def _ohos_meson_test():
                    self.run(
                        'meson test -v -C "{}" --timeout-multiplier=16 '
                        "--no-rebuild --no-suite=failing".format(build_folder)
                    )

                meson.test = _ohos_meson_test

            meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
