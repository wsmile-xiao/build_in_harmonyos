#!/usr/bin/env python3
"""Conan recipe — libsignon-glib 2.1 (Meson)"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps


class LibsignonGlibConan(ConanFile):
    name = "libsignon-glib"
    version = "2.1"
    description = "GLib-based library for Signon authentication framework"
    license = "LGPL-2.1"
    homepage = "https://gitlab.com/accounts-sso/libsignon-glib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0.1")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["tests"] = "false"
        tc.project_options["python"] = "false"
        tc.project_options["introspection"] = "false"
        tc.project_options["documentation"] = "false"
        tc.project_options["debugging"] = "false"
        # Discover toolchain binaries dynamically (R33: no hardcoded paths)
        ar_path = shutil.which("llvm-ar") or shutil.which("ar")
        if ar_path:
            tc.ar = ar_path
        strip_path = shutil.which("llvm-strip") or shutil.which("strip")
        if strip_path:
            tc.strip = strip_path

        # Add glib package's pkgconfig directory to pkg_config_path
        glib_info = self.dependencies["glib"]
        glib_root = glib_info.package_folder
        if glib_root:
            glib_pc = os.path.join(glib_root, "lib", "pkgconfig")
            if os.path.isdir(glib_pc):
                tc.pkg_config_path = tc.pkg_config_path + ":" + glib_pc

        tc.generate()

        # Generate pkg-config files for dependencies
        pc = PkgConfigDeps(self)
        pc.generate()

        # Patch conan-generated .pc files with missing glib tool variables
        self._patch_pc_files()

    def _patch_pc_files(self):
        """Add missing glib tool variables to conan-generated pkg-config files."""
        glib_info = self.dependencies["glib"]
        glib_root = glib_info.package_folder
        if not glib_root:
            return

        bindir = os.path.join(glib_root, "bin")
        gen_folder = self.generators_folder

        pc_patches = {
            "gio-2.0.pc": {"gdbus_codegen": os.path.join(bindir, "gdbus-codegen")},
            "glib-2.0.pc": {
                "glib_mkenums": os.path.join(bindir, "glib-mkenums"),
                "glib_genmarshal": os.path.join(bindir, "glib-genmarshal"),
            },
        }

        for pc_file, variables in pc_patches.items():
            pc_path = os.path.join(gen_folder, pc_file)
            if not os.path.exists(pc_path):
                self.output.info(f"PkgConfigDeps file not found: {pc_path}")
                continue
            with open(pc_path, "r") as f:
                content = f.read()
            additions = []
            for var_name, var_value in variables.items():
                if var_name + "=" not in content:
                    additions.append(f"{var_name}={var_value}")
            if additions:
                addition_text = "\n".join(additions) + "\n"
                if "Name:" in content:
                    content = content.replace("Name:", addition_text + "Name:", 1)
                else:
                    content = addition_text + content
                with open(pc_path, "w") as f:
                    f.write(content)
                self.output.info(f"Patched {pc_file} with: {', '.join(additions)}")

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["signon-glib"]
        self.cpp_info.set_property("pkg_config_name", "libsignon-glib")
