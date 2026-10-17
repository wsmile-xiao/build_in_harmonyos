#!/usr/bin/env python3
"""Conan recipe — sound-juicer 3.40.0 (Meson).

Sound Juicer is a CD ripper for GNOME. Libraries not published in the OHOS
conan registry (brasero, musicbrainz5, discid, canberra-gtk, gst-plugins-base
pbutils) are stubbed via the HAVE_STUB_DEPS build flag (see patches and
libjuicer/stub-ohos.c). Real dependencies: glib, gstreamer, gtk,
gsettings-desktop-schemas, iso-codes.

Dependency-graph note: gtk/3.24.43 pins glib/2.84.0.1 (which requires
zlib/1.3.1.1) while gstreamer/1.28.3 pins glib2/2.88.0 (zlib/1.3.1). The
zlib requirement is force-aligned to 1.3.1.1 so the graph resolves, and
PkgConfigDeps gives the canonical glib-2.0.pc name to the glib package, so
the whole application links against a single shared glib.
"""
import os
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class SoundJuicerConan(ConanFile):
    name = "sound-juicer"
    version = "3.40.0"
    description = "CD ripper for GNOME (stub deps for OHOS portability)"
    license = "GPL-2.0-or-later"
    homepage = "https://wiki.gnome.org/Apps/SoundJuicer"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    generators = ("PkgConfigDeps",)

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # glib provides glib-2.0/gobject-2.0/gio-2.0/gmodule-2.0/gthread-2.0
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        # gstreamer provides gstreamer-1.0 (core only; pbutils is stubbed)
        self.requires("gstreamer/1.28.3", transitive_headers=True, transitive_libs=True)
        # gtk provides gtk+-3.0
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        # real data/header dependencies
        self.requires("gsettings-desktop-schemas/49.1")
        self.requires("iso-codes/4.20.1")
        # gtk pins glib/2.84.0.1 (zlib/1.3.1.1) while gstreamer pins
        # glib2/2.88.0 (zlib/1.3.1) — force one zlib to resolve the graph.
        self.requires("zlib/1.3.1.1", force=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # The CI worker exports AR/AS/STRIP/NM/RANLIB as llvm-* names that are
        # not on PATH; meson probes them and aborts at configure. Drop the
        # broken env values and pin the real tools by ABSOLUTE path (same
        # workaround as the glib2/gstreamer/gtk recipes).
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
        tc.project_options["default_library"] = "static"
        tc.generate()

        # The conan gstreamer package generates gstreamer.pc (no -1.0 suffix);
        # sound-juicer's meson.build looks for gstreamer-1.0. Write a redirect
        # .pc into the generators folder (on PKG_CONFIG_PATH).
        gst = self.dependencies["gstreamer"]
        redirect = os.path.join(self.generators_folder, "gstreamer-1.0.pc")
        with open(redirect, "w", encoding="utf-8", newline="\n") as f:
            f.write(
                "Name: gstreamer-1.0\n"
                "Description: GStreamer redirect (conan package name: gstreamer)\n"
                f"Version: {gst.ref.version}\n"
                "Requires: gstreamer\n"
            )

        # meson's gnome module resolves glib-compile-schemas /
        # glib-compile-resources through the gio-2.0 pkg-config variable; the
        # conan-generated pc lacks it. Point at the signed tool copies that
        # _prepare_native_tools() creates in build().
        tools_folder = os.path.join(self.build_folder, "conan-native-tools")
        gio_pc = os.path.join(self.generators_folder, "gio-2.0.pc")
        if os.path.isfile(gio_pc):
            with open(gio_pc, "a", encoding="utf-8", newline="\n") as f:
                f.write(f"glib_compile_schemas={tools_folder}/glib-compile-schemas\n")
                f.write(f"glib_compile_resources={tools_folder}/glib-compile-resources\n")

        # glib was built with proxy-libintl: glib/gi18n.h maps gettext() to
        # g_libintl_* symbols that live in the glib package's libintl.so —
        # append -lintl to the generated glib-2.0.pc Libs (same as the gtk
        # recipe's _augment_glib_pkg_config).
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if os.path.isfile(glib_pc):
            with open(glib_pc, encoding="utf-8") as f:
                lines = f.read().splitlines(keepends=True)
            out = []
            for line in lines:
                if line.startswith("Libs:") and "-lintl" not in line.split():
                    line = line.rstrip("\r\n") + " -lintl\n"
                out.append(line)
            with open(glib_pc, "w", encoding="utf-8", newline="\n") as f:
                f.write("".join(out))

    # ── OHOS build tools (glib/gtk binaries must be re-signed to run) ──

    def _sign_elf(self, binary):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise FileNotFoundError(f"HarmonyOS signer missing: {signer}")
        self.run(shlex.join([signer, "sign", "-inFile", binary,
                             "-outFile", binary, "-selfSign", "1"]))

    def _native_tools_folder(self):
        return os.path.join(self.build_folder, "conan-native-tools")

    def _prepare_native_tools(self):
        """Copy the glib/gtk build tools needed by meson's gnome module
        (glib-compile-resources, glib-compile-schemas, gtk-update-icon-cache)
        into the build folder and re-sign them for OHOS execution (mirrors
        the gtk/3.24.43 recipe)."""
        tools_folder = self._native_tools_folder()
        os.makedirs(tools_folder, exist_ok=True)
        sources = []
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        for tool in ("glib-compile-resources", "glib-compile-schemas"):
            sources.append(os.path.join(glib_bin, tool))
        gtk_bin = os.path.join(self.dependencies["gtk"].package_folder, "bin")
        sources.append(os.path.join(gtk_bin, "gtk-update-icon-cache"))
        for src in sources:
            if not os.path.isfile(src):
                raise FileNotFoundError(f"build tool missing: {src}")
            dst = os.path.join(tools_folder, os.path.basename(src))
            if os.path.isfile(dst):
                # already copied+signed in build(); re-copy over a signed
                # binary fails with EPERM — reuse the existing copy
                continue
            shutil.copyfile(src, dst)
            os.chmod(dst, 0o755)
            if self.settings.os == "OHOS":
                self._sign_elf(dst)

    def _build_environment(self):
        env = Environment()
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env.define_path("TMPDIR", tmp)
        env.define_path("TMP", tmp)
        env.define_path("TEMP", tmp)
        env.prepend_path("PATH", self._native_tools_folder())
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        return env

    def build(self):
        # Ensure meson/ninja are available
        if not shutil.which("meson"):
            self.run(f"{sys.executable} -m pip install --user meson")
        if not shutil.which("ninja"):
            self.run(f"{sys.executable} -m pip install --user ninja")

        self._prepare_native_tools()
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()

    def package(self):
        self._prepare_native_tools()
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
