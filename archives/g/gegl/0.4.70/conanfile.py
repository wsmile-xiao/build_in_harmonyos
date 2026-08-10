#!/usr/bin/env python3
"""Conan recipe — gegl 0.4.70 (Meson).

Generic Graphics Library - graph-based image processing framework.
Core engine for GIMP 2.10+ and other image processing tools.
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain


class GeglConan(ConanFile):
    name = "gegl"
    version = "0.4.70"
    description = "Generic Graphics Library - graph-based image processing framework"
    license = "GPL-3.0"
    homepage = "https://gegl.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        self.requires("babl/0.1.126")
        self.requires("glib/2.84.0.1")
        self.requires("json-glib/1.10.6")
        self.requires("libpng/1.6.58")
        self.requires("libjpeg/10")
        self.requires("libtiff/4.7.2")
        self.requires("libwebp/1.6.0")
        self.requires("cairo/1.18.4")
        self.requires("pango/1.56.4")
        self.requires("fftw/3.3.10.1")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build"

    def _fix_glib_pc_files(self):
        """Fix generated glib .pc files: add glib_mkenums variable, -lintl, and gio-unix-2.0.pc."""
        gens = self.generators_folder

        glib_prefix = None
        glib_pc = os.path.join(gens, "glib-2.0.pc")
        if os.path.isfile(glib_pc):
            with open(glib_pc) as f:
                for line in f:
                    if line.startswith("prefix="):
                        glib_prefix = line.strip().split("=", 1)[1]
                        glib_prefix = glib_prefix.strip('"').strip("'")
                        break

        if glib_prefix:
            bindir = os.path.join(glib_prefix, "bin")
        else:
            return

        for pc_name in ("glib-2.0.pc", "gobject-2.0.pc",
                        "gmodule-2.0.pc", "gthread-2.0.pc", "gio-2.0.pc"):
            pc_path = os.path.join(gens, pc_name)
            if not os.path.isfile(pc_path):
                continue
            with open(pc_path) as f:
                content = f.read()
            modified = False
            if "glib_mkenums" not in content:
                content += f"\nglib_genmarshal={bindir}/glib-genmarshal\n"
                content += f"gobject_query={bindir}/gobject-query\n"
                content += f"glib_mkenums={bindir}/glib-mkenums\n"
                modified = True
            if "-lintl" not in content:
                lines = content.splitlines(True)
                new_lines = []
                for line in lines:
                    if line.startswith("Libs:") and "-lintl" not in line:
                        line = line.rstrip("\n") + " -lintl\n"
                    new_lines.append(line)
                content = "".join(new_lines)
                modified = True
            if modified:
                with open(pc_path, "w") as f:
                    f.write(content)

        # Create gio-unix-2.0.pc from gio-2.0.pc (meson needs this separate .pc file)
        gio_unix_pc = os.path.join(gens, "gio-unix-2.0.pc")
        gio_pc = os.path.join(gens, "gio-2.0.pc")
        if not os.path.isfile(gio_unix_pc) and os.path.isfile(gio_pc):
            with open(gio_pc) as f:
                gio_content = f.read()
            # Create gio-unix-2.0.pc with gio-unix-2.0 as the pkg_config_name
            gio_unix_content = gio_content.replace(
                "Description: Conan component: gio-2.0",
                "Description: Conan component: gio-unix-2.0"
            )
            gio_unix_content = gio_unix_content.replace(
                "Name: gio-2.0",
                "Name: gio-unix-2.0"
            )
            with open(gio_unix_pc, "w") as f:
                f.write(gio_unix_content)

    def _inject_meson_binaries(self):
        """Inject ar/ranlib/pkg-config into conan_meson_native.ini."""
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = ce.get("ar")
        rl = ce.get("ranlib")
        if not ar:
            cc = ce.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                for name in ("llvm-ar", "ar"):
                    cand = os.path.join(bindir, name)
                    if os.path.isfile(cand):
                        ar = cand
                        break
                for name in ("llvm-ranlib", "ranlib"):
                    rlc = os.path.join(bindir, name)
                    if os.path.isfile(rlc):
                        rl = rlc
                        break
        pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        for nf_name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, nf_name)
            if not os.path.isfile(nf):
                continue
            with open(nf) as f:
                content = f.read()
            if "[binaries]" not in content:
                continue
            new_lines = []
            for line in content.splitlines(True):
                new_lines.append(line)
                if line.strip() == "[binaries]":
                    if ar and "\nar =" not in content:
                        new_lines.append("ar = '%s'\n" % ar)
                    if rl and "\nranlib =" not in content:
                        new_lines.append("ranlib = '%s'\n" % rl)
                    if pkg_config and "\npkg-config =" not in content:
                        new_lines.append("pkg-config = '%s'\n" % pkg_config)
            new_content = "".join(new_lines)
            if new_content != content:
                with open(nf, "w") as f:
                    f.write(new_content)

    def _fix_pango_pc_files(self):
        """Create pangocairo.pc from pango.pc (pango package bundles all libs in one component)."""
        gens = self.generators_folder
        pango_pc = os.path.join(gens, "pango.pc")
        pangocairo_pc = os.path.join(gens, "pangocairo.pc")

        if os.path.isfile(pango_pc) and not os.path.isfile(pangocairo_pc):
            with open(pango_pc) as f:
                content = f.read()
            # Replace Name and Description to match pangocairo
            content = content.replace("Name: pango", "Name: pangocairo")
            content = content.replace("Description: Conan component: pango",
                                      "Description: Conan component: pangocairo")
            # Replace lib reference from pango-1.0 to pangocairo-1.0
            content = content.replace("-lpango-1.0", "-lpangocairo-1.0 -lpango-1.0")
            with open(pangocairo_pc, "w") as f:
                f.write(content)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._fix_glib_pc_files()
        self._fix_pango_pc_files()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["introspection"] = "false"
        tc.project_options["docs"] = "false"
        tc.project_options["gtk-doc"] = "false"
        tc.project_options["workshop"] = "false"
        # Enable available optional deps
        tc.project_options["cairo"] = "enabled"
        tc.project_options["pango"] = "enabled"
        tc.project_options["pangocairo"] = "enabled"
        tc.project_options["gdk-pixbuf"] = "auto"
        tc.project_options["webp"] = "enabled"
        tc.project_options["libtiff"] = "enabled"
        # Disable unavailable optional deps
        tc.project_options["gexiv2"] = "disabled"
        tc.project_options["lcms"] = "disabled"
        tc.project_options["lensfun"] = "disabled"
        tc.project_options["libraw"] = "disabled"
        tc.project_options["librsvg"] = "disabled"
        tc.project_options["libspiro"] = "disabled"
        tc.project_options["openexr"] = "disabled"
        tc.project_options["poppler"] = "disabled"
        tc.project_options["maxflow"] = "disabled"
        tc.project_options["umfpack"] = "disabled"
        tc.project_options["libav"] = "disabled"
        tc.project_options["lua"] = "disabled"
        tc.project_options["mrg"] = "disabled"
        tc.project_options["jasper"] = "disabled"
        tc.project_options["libv4l"] = "disabled"
        tc.project_options["libv4l2"] = "disabled"
        tc.project_options["sdl1"] = "disabled"
        tc.project_options["pygobject"] = "disabled"
        tc.project_options["vapigen"] = "disabled"
        tc.generate()
        self._inject_meson_binaries()

    def build(self):
        if not shutil.which("meson"):
            self.run(f"{sys.executable} -m pip install --user meson")
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "GEGL")
        self.cpp_info.set_property("pkg_config_name", "gegl-0.4")

        gegl = self.cpp_info.components["gegl-0.4"]
        gegl.set_property("cmake_target_name", "GEGL::GEGL")
        gegl.set_property("pkg_config_name", "gegl-0.4")
        gegl.libs = ["gegl-0.4"]
        gegl.includedirs = ["include/gegl-0.4"]
        gegl.libdirs = ["lib"]
        gegl.requires = [
            "babl::babl",
            "glib::glib-2.0", "glib::gobject-2.0", "glib::gio-2.0",
            "json-glib::json-glib-1.0",
            "libpng::libpng",
            "libjpeg::libjpeg",
            "libtiff::libtiff",
            "libwebp::libwebp",
            "cairo::cairo",
            "pango::pango",
            "fftw::fftw",
        ]
        if self.settings.os in ("Linux", "OHOS"):
            gegl.system_libs = ["m", "pthread", "dl"]
