#!/usr/bin/env python3
"""Conan recipe for lxc-templates-legacy 3.0.4 — LXC container template scripts.

This is a script-only project: no compilation, just shell scripts and config files.
The conanfile generates template scripts from .in files using sed (like configure
does) and installs them directly, avoiding the autotools build system entirely.
This bypasses HMDFS config.status permission issues (E011/E052).
"""
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LxcTemplatesLegacyConan(ConanFile):
    name = "lxc-templates-legacy"
    version = "3.0.4"
    description = "LXC container template scripts - legacy version"
    license = "MIT"
    homepage = "https://linuxcontainers.org/lxc/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder

        # Generate template scripts from .in files (what configure/config.status does)
        # This replaces autotools configure, avoiding HMDFS E011/E052 permission issues
        templates_dir = os.path.join(src, "templates")
        if os.path.isdir(templates_dir):
            for in_file in os.listdir(templates_dir):
                if in_file.endswith(".in"):
                    out_file = in_file[:-3]
                    out_path = os.path.join(templates_dir, out_file)
                    in_path = os.path.join(templates_dir, in_file)
                    with open(in_path) as f:
                        content = f.read()
                    replacements = {
                        "@PACKAGE_VERSION@": self.version,
                        "@PACKAGE_NAME@": "lxc-templates",
                        "@PACKAGE_BUGREPORT@": "",
                        "@LXCTEMPLATEDIR@": "/usr/share/lxc/templates",
                        "@DATADIR@": "/usr/share",
                        "@PREFIX@": "/usr",
                        "@BINDIR@": "/usr/bin",
                        "@SYSCONFDIR@": "/etc",
                        "@LIBDIR@": "/usr/lib",
                        "@LOCALSTATEDIR@": "/var",
                        "@TEMPLATEDIR@": "/usr/share/lxc/templates",
                    }
                    for k, v in replacements.items():
                        content = content.replace(k, v)
                    content = re.sub(r"@[A-Z_]+@", "", content)
                    with open(out_path, "w") as f:
                        f.write(content)
                    os.chmod(out_path, 0o755)

        # Generate config files from .in files if any
        config_dir = os.path.join(src, "config")
        if os.path.isdir(config_dir):
            for in_file in os.listdir(config_dir):
                if in_file.endswith(".in"):
                    out_file = in_file[:-3]
                    out_path = os.path.join(config_dir, out_file)
                    in_path = os.path.join(config_dir, in_file)
                    with open(in_path) as f:
                        content = f.read()
                    content = content.replace("@PACKAGE_VERSION@", self.version)
                    content = re.sub(r"@[A-Z_]+@", "", content)
                    with open(out_path, "w") as f:
                        f.write(content)

    def package(self):
        """Install template scripts and config files."""
        src = self.source_folder
        pkg = self.package_folder

        # Install template scripts
        templates_src = os.path.join(src, "templates")
        templates_dst = os.path.join(pkg, "usr", "share", "lxc", "templates")
        os.makedirs(templates_dst, exist_ok=True)
        if os.path.isdir(templates_src):
            for f in os.listdir(templates_src):
                if f.startswith("lxc-") and not f.endswith(".in"):
                    src_file = os.path.join(templates_src, f)
                    dst_file = os.path.join(templates_dst, f)
                    if os.path.isfile(src_file):
                        shutil.copy2(src_file, dst_file)
                        os.chmod(dst_file, 0o755)

        # Install config files
        config_src = os.path.join(src, "config")
        config_dst = os.path.join(pkg, "usr", "share", "lxc", "config")
        os.makedirs(config_dst, exist_ok=True)
        if os.path.isdir(config_src):
            for f in os.listdir(config_src):
                src_file = os.path.join(config_src, f)
                dst_file = os.path.join(config_dst, f)
                if os.path.isfile(src_file) and f.endswith(".conf"):
                    shutil.copy2(src_file, dst_file)

        # Create var directories
        os.makedirs(os.path.join(pkg, "var", "lib", "lxc"), exist_ok=True)
        os.makedirs(os.path.join(pkg, "var", "cache", "lxc"), exist_ok=True)

    def package_info(self):
        # Script-only package: no libraries, no binaries
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share"]
