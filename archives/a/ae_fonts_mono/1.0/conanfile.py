#!/usr/bin/env python3
"""Conan recipe — ae_fonts_mono 1 (Arabeyes Arabic monospace font data package).

Pure font data package: installs 10x21.bdf and 10x21.pcf under
share/fonts/ae_fonts_mono/. No binaries or libraries are produced
(FreeBSD port marks NO_BUILD=yes).
"""
import os
import shutil
import hashlib
import tarfile
import subprocess

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AefontsmonoConan(ConanFile):
    name = "ae_fonts_mono"
    version = "1.0"
    description = "Arabeyes Arabic monospace font (10x21 BDF/PCF)"
    license = "LicenseRef-public-domain"
    homepage = "https://www.arabeyes.org/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27: No external Conan dependencies — data-only package
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # Use curl -kL to download (SSL workaround for HarmonyOS).
        # Resolve curl path explicitly: conan buildenv may not include /usr/bin.
        curl = shutil.which("curl") or "/usr/bin/curl"
        src_url = self.conan_data["sources"]["url"]
        expected_sha256 = self.conan_data["sources"]["sha256"]
        tarball_path = os.path.join(self.source_folder, "ae_fonts_mono.tar.bz2")

        subprocess.run(
            [curl, "-kL", "-o", tarball_path, src_url],
            check=True,
            capture_output=True,
        )

        # Verify sha256
        actual_sha256 = hashlib.sha256(open(tarball_path, "rb").read()).hexdigest()
        if actual_sha256 != expected_sha256:
            raise Exception(
                f"SHA256 mismatch: expected {expected_sha256}, got {actual_sha256}"
            )

        # Extract tarball, strip single top-level directory (ae_fonts_mono/)
        tmp_extract = os.path.join(self.source_folder, "_tmp_extract")
        os.makedirs(tmp_extract, exist_ok=True)
        with tarfile.open(tarball_path, "r:bz2") as tf:
            tf.extractall(tmp_extract)

        entries = os.listdir(tmp_extract)
        if len(entries) == 1 and os.path.isdir(os.path.join(tmp_extract, entries[0])):
            top_dir = os.path.join(tmp_extract, entries[0])
            for item in os.listdir(top_dir):
                shutil.move(os.path.join(top_dir, item), self.source_folder)
            shutil.rmtree(tmp_extract)
        else:
            for item in entries:
                shutil.move(os.path.join(tmp_extract, item), self.source_folder)
            shutil.rmtree(tmp_extract)

        os.unlink(tarball_path)

    def build(self):
        # NO_BUILD=yes — pure font data package, nothing to compile.
        # apply_conandata_patches is a no-op with empty patches (G1 gate).
        apply_conandata_patches(self)
        pass

    def package(self):
        # Install font files into share/fonts/ae_fonts_mono/
        font_dir = os.path.join(self.package_folder, "share", "fonts", "ae_fonts_mono")
        os.makedirs(font_dir, exist_ok=True)
        for fname in ("10x21.bdf", "10x21.pcf"):
            src = os.path.join(self.source_folder, fname)
            if not os.path.exists(src):
                raise Exception(f"Source file missing: {src}")
            shutil.copy(src, font_dir)

        # pkg-config file so consumers can locate the font dir (G4 artifact)
        pkgconfig_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        os.makedirs(pkgconfig_dir, exist_ok=True)
        pc_content = (
            "prefix=${pcfiledir}/../..\n"
            "fontdir=${prefix}/share/fonts/ae_fonts_mono\n"
            "\n"
            "Name: ae_fonts_mono\n"
            "Description: Arabeyes Arabic monospace font (10x21 BDF/PCF)\n"
            "Version: 1\n"
        )
        with open(os.path.join(pkgconfig_dir, "ae_fonts_mono.pc"), "w") as f:
            f.write(pc_content)

    def package_info(self):
        # Data-only package: no libraries to link
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("pkg_config_name", "ae_fonts_mono")
