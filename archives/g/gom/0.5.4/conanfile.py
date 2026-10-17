#!/usr/bin/env python3
"""Conan recipe — gom 0.5.4 (Meson).

GObject to SQLite object mapper library (GNOME). Maps GObject classes onto
SQLite tables: repository/adapters, resources, filters, sorting, migrations.
"""
import glob
import os
import shlex
import shutil
import sys

from conan import ConanFile
from conan.tools.files import (
    check_sha256,
    get,
    unzip,
    apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain


class GomConan(ConanFile):
    name = "gom"
    version = "0.5.4"
    description = "GObject to SQLite object mapper library (GNOME)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gom"
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
        # glib provides glib-2.0/gobject-2.0/gio-2.0; sqlite3 is the backend.
        # gdk-pixbuf is required by the top-level meson.build dependency()
        # unconditionally (used by the test-gom-transform test).
        self.requires("glib/2.84.0.1")
        self.requires("sqlite3/3.49.1")
        self.requires("gdk-pixbuf/2.44.6")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build"

    def _fix_glib_pc_files(self):
        """Fix generated glib .pc files: add glib_mkenums variable and -lintl."""
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

    def source(self):
        sources = dict(self.conan_data["sources"])
        mirror_url = sources.pop("mirror_url", None)
        staged_source = os.path.expanduser(
            "~/Download/gom-0.5.4.tar.xz"
        )
        if os.path.isfile(staged_source):
            check_sha256(self, staged_source, sources["sha256"])
            unzip(self, staged_source, strip_root=True)
            return
        try:
            get(self, **sources, strip_root=True)
        except Exception as error:
            if not mirror_url:
                raise
            self.output.warning(f"Primary source failed ({error}), trying mirror")
            get(self, url=mirror_url, sha256=sources["sha256"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._fix_glib_pc_files()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["enable-introspection"] = "false"
        tc.project_options["enable-gtk-doc"] = "false"
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
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def _sign_installed_elfs(self):
        """Sign packaged ELF files so they can be loaded/executed on OHOS."""
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip package signing")
            return
        patterns = [
            os.path.join(self.package_folder, "bin", "*"),
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        ]
        candidates = []
        for pattern in patterns:
            candidates.extend(glob.glob(pattern, recursive=True))
        for binary in sorted(set(candidates)):
            if not os.path.isfile(binary) or os.path.islink(binary):
                continue
            self._sign_elf(binary)

    def _sign_elf(self, binary):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise FileNotFoundError(f"HarmonyOS binary signer is missing: {signer}")
        self.run(
            shlex.join(
                [
                    signer,
                    "sign",
                    "-inFile",
                    binary,
                    "-outFile",
                    binary,
                    "-selfSign",
                    "1",
                ]
            )
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "gom")
        self.cpp_info.set_property("pkg_config_name", "gom-1.0")

        gom = self.cpp_info.components["gom-1.0"]
        gom.set_property("cmake_target_name", "gom::gom")
        gom.set_property("pkg_config_name", "gom-1.0")
        gom.libs = ["gom-1.0"]
        gom.includedirs = ["include/gom-1.0"]
        gom.libdirs = ["lib"]
        gom.requires = ["glib::glib-2.0", "glib::gobject-2.0", "glib::gio-2.0", "sqlite3::sqlite3", "gdk-pixbuf::gdk-pixbuf"]
        if self.settings.os in ("Linux", "OHOS"):
            gom.system_libs = ["intl"]
