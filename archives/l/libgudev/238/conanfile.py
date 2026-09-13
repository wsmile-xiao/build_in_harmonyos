#!/usr/bin/env python3
"""Conan recipe — libgudev 238 (Meson).

GObject bindings for libudev (formerly part of udev/systemd, now a
standalone GNOME project). Used by colord for device enumeration
(hard dependency: `gudev = dependency('gudev-1.0', ...)`).

OHOS adaptation notes:
- Dependencies: glib-2.0/gobject-2.0 (glib package) and libudev
  (provided by libudev-zero/1.0.4, whose libudev.pc declares
  Version: 251 — satisfies libgudev's `libudev >= 251`).
- Self-tests (test-enumerator-filter / test-sysfsattr) need gio +
  umockdev with LD_PRELOAD, which is unavailable on OHOS ->
  -Dtests=disabled.
- vapi/introspection/gtk_doc are desktop niceties -> disabled.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain


class LibGudevConan(ConanFile):
    name = "libgudev"
    version = "238"
    description = "GObject bindings for libudev"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libgudev"
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
        self.requires("libudev-zero/1.0.4")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build"

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
        self._copy_libudev_pc()
        self._fix_glib_pc_files()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["tests"] = "disabled"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["vapi"] = "disabled"
        tc.project_options["gtk_doc"] = "false"
        tc.generate()
        self._inject_meson_binaries()

    def _fix_glib_pc_files(self):
        """Fix generated glib .pc files: add glib_mkenums variable and -lintl.

        gnome.mkenums() reads the glib_mkenums pkg-config variable from
        glib-2.0.pc to locate the glib-mkenums tool; the conan-generated
        .pc files lack it, so add it (same fix as the json-glib recipe).
        """
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
        if not glib_prefix:
            return
        bindir = os.path.join(glib_prefix, "bin")
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

    def _copy_libudev_pc(self):
        """Generate a correct libudev.pc into the generators folder.

        libudev-zero's package_info does not set a pkg_config_name, so
        PkgConfigDeps does not emit libudev.pc; meson's pkg-config lookup
        would otherwise fail with "Dependency libudev not found". The
        libudev.pc shipped inside the libudev-zero package has a broken
        prefix (two absolute paths concatenated), so we regenerate it with
        the package's own folder as prefix (its Version is 251, which
        satisfies libgudev's `libudev >= 251`).
        """
        if "libudev-zero" not in self.dependencies:
            return
        dep = self.dependencies["libudev-zero"]
        prefix = dep.package_folder
        pc_content = (
            "# SPDX-License-Identifier: ISC\n"
            f"prefix={prefix}\n"
            f"exec_prefix=${{prefix}}\n"
            "libdir=${exec_prefix}/lib\n"
            "includedir=${prefix}/include\n"
            "\n"
            "Name: libudev\n"
            "Description: Daemonless replacement for libudev\n"
            "Version: 251\n"
            "URL: https://github.com/illiliti/libudev-zero\n"
            "Libs: -L${libdir} -ludev\n"
            "Cflags: -I${includedir}\n"
        )
        dest = os.path.join(self.generators_folder, "libudev.pc")
        with open(dest, "w") as f:
            f.write(pc_content)
        self.output.info("Regenerated libudev.pc (Version=251) into generators folder")

    def _pc_version(self, pc_path):
        try:
            with open(pc_path) as f:
                for line in f:
                    if line.startswith("Version:"):
                        return line.strip().split(":", 1)[1].strip()
        except OSError:
            pass
        return "?"

    def build(self):
        if not shutil.which("meson"):
            self.run("python3 -m pip install --user meson")
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        """OHOS ELF codesign (binary-sign-tool), same as libusb/glib recipes."""
        if str(self.settings.os) != "OHOS" or not self.options.shared:
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            return
        libdir = os.path.join(self.package_folder, "lib")
        for root, _, files in os.walk(libdir):
            for filename in files:
                if ".so" not in filename:
                    continue
                path = os.path.join(root, filename)
                if os.path.islink(path):
                    continue
                subprocess.run([objcopy, "--remove-section", ".codesign", path], check=False)
                signed = path + ".signed"
                subprocess.run([signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"], check=True)
                os.replace(signed, path)
                os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "gudev")
        self.cpp_info.set_property("pkg_config_name", "gudev-1.0")

        gudev = self.cpp_info.components["gudev-1.0"]
        gudev.set_property("cmake_target_name", "gudev::gudev")
        gudev.set_property("pkg_config_name", "gudev-1.0")
        gudev.libs = ["gudev-1.0"]
        gudev.includedirs = ["include/gudev-1.0"]
        gudev.libdirs = ["lib"]
        gudev.requires = ["glib::glib-2.0", "glib::gobject-2.0", "libudev-zero::libudev-zero"]
