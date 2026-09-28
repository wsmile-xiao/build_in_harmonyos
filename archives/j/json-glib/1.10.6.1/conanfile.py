#!/usr/bin/env python3
"""Conan recipe — json-glib 1.10.6 (Meson).

JSON library for GLib/GObject based applications.
Required dependency for GEGL's operation graph serialization.
"""
import glob
import os
import shutil
import sys

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain


class JsonGlibConan(ConanFile):
    name = "json-glib"
    version = "1.10.6.1"
    description = "JSON library for GLib/GObject based applications"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/json-glib"
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
        self.requires("glib/2.84.0.1")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build"

    def _fix_glib_pc_files(self):
        """Fix generated glib .pc files: add glib_mkenums variable and -lintl."""
        gens = self.generators_folder

        # Find glib prefix from the generated glib-2.0.pc
        glib_prefix = None
        glib_pc = os.path.join(gens, "glib-2.0.pc")
        if os.path.isfile(glib_pc):
            with open(glib_pc) as f:
                for line in f:
                    if line.startswith("prefix="):
                        glib_prefix = line.strip().split("=", 1)[1]
                        # Strip quotes if present
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
            # Add glib_mkenums and related tool variables if missing
            if "glib_mkenums" not in content:
                content += f"\nglib_genmarshal={bindir}/glib-genmarshal\n"
                content += f"gobject_query={bindir}/gobject-query\n"
                content += f"glib_mkenums={bindir}/glib-mkenums\n"
                modified = True
            # Add -lintl to Libs if missing
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
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._fix_glib_pc_files()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["tests"] = "true"
        tc.project_options["conformance"] = "true"
        tc.project_options["documentation"] = "disabled"
        tc.project_options["man"] = "false"
        # OHOS 上 gettext msgfmt 被 glib proxy libintl 遮蔽（symbol not found），
        # nls 翻译与本库功能无关，禁用避免 po/ 构建失败（libdbusmenu 同类问题）。
        tc.project_options["nls"] = "disabled"
        tc.generate()
        self._inject_meson_binaries()

    def build(self):
        if not shutil.which("meson"):
            self.run(f"{sys.executable} -m pip install --user meson")
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # rule4: 上游测试必须在 build() 真实执行（meson test，含 conformance 330 子测试）。
        # json-glib 测试为纯 JSON 解析（无 dbus/图形依赖），本地实测 17/17 通过。
        meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        """OHOS loader rejects unsigned .so with 'Permission denied'. json-glib
        ships a shared library consumed at runtime by libdbusmenu/gegl etc., so
        codesign every installed .so after meson install (glib precedent)."""
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        candidates_objcopy = [
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy") or "",
        ]
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        if cc:
            candidates_objcopy.insert(0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
        objcopy = next((p for p in candidates_objcopy if p and os.path.isfile(p)), None)
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign (cross/SDK env)")
            return
        for so in sos:
            if objcopy:
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "json-glib")
        self.cpp_info.set_property("pkg_config_name", "json-glib-1.0")

        jg = self.cpp_info.components["json-glib-1.0"]
        jg.set_property("cmake_target_name", "json-glib::json-glib")
        jg.set_property("pkg_config_name", "json-glib-1.0")
        jg.libs = ["json-glib-1.0"]
        jg.includedirs = ["include/json-glib-1.0"]
        jg.libdirs = ["lib"]
        jg.requires = ["glib::glib-2.0", "glib::gobject-2.0", "glib::gio-2.0"]
        if self.settings.os in ("Linux", "OHOS"):
            jg.system_libs = ["intl"]
