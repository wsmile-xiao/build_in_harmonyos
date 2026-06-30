#!/usr/bin/env python3
"""Conan recipe — fonts-encodings 1.1.0 (X.Org font encoding data package).

This is a data-only package: it installs .enc.gz files and encodings.dir
under share/fonts/X11/encodings/. No binaries or libraries are produced.
"""
import os
import shutil
import hashlib
import tarfile
import subprocess
import stat

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class FontsEncodingsConan(ConanFile):
    name = "fonts-encodings"
    version = "1.1.0"
    description = "X.Org font encoding data files"
    license = "LicenseRef-Homebrew-public-domain"
    homepage = "https://www.x.org/"
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
        # Use curl -kL to download (SSL workaround for HarmonyOS)
        src_url = self.conan_data["sources"]["url"]
        expected_sha256 = self.conan_data["sources"]["sha256"]
        tarball_path = os.path.join(self.source_folder, "encodings-1.1.0.tar.xz")

        # Download with curl -kL
        subprocess.run(
            ["curl", "-kL", "-o", tarball_path, src_url],
            check=True,
            capture_output=True,
        )

        # Verify sha256
        actual_sha256 = hashlib.sha256(open(tarball_path, "rb").read()).hexdigest()
        if actual_sha256 != expected_sha256:
            raise Exception(
                f"SHA256 mismatch: expected {expected_sha256}, got {actual_sha256}"
            )

        # Extract to a temp directory first, then move with strip_root
        tmp_extract = os.path.join(self.source_folder, "_tmp_extract")
        os.makedirs(tmp_extract, exist_ok=True)

        with tarfile.open(tarball_path, "r:xz") as tf:
            tf.extractall(tmp_extract)

        # Find the top-level directory and move its contents to source_folder
        entries = os.listdir(tmp_extract)
        if len(entries) == 1 and os.path.isdir(os.path.join(tmp_extract, entries[0])):
            # Single top-level directory — strip it
            top_dir = os.path.join(tmp_extract, entries[0])
            for item in os.listdir(top_dir):
                src = os.path.join(top_dir, item)
                dst = os.path.join(self.source_folder, item)
                shutil.move(src, dst)
            shutil.rmtree(tmp_extract)
        else:
            # No top-level directory — move everything
            for item in entries:
                src = os.path.join(tmp_extract, item)
                dst = os.path.join(self.source_folder, item)
                shutil.move(src, dst)
            shutil.rmtree(tmp_extract)

        # Remove the tarball
        os.unlink(tarball_path)

        # Fix permissions: ensure configure and other scripts are executable
        for script in ["configure", "install-sh", "missing", "config.guess", "config.sub"]:
            script_path = os.path.join(self.source_folder, script)
            if os.path.exists(script_path):
                os.chmod(script_path, 0o755)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Static linking flag (no-op for data package, but required by rule)
        tc.extra_ldflags.append("-static")
        # Set font root dir relative to prefix so package layout is correct
        tc.configure_args.append("--with-fontrootdir=${prefix}/share/fonts/X11")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Patch config.guess for HarmonyOS platform detection
        config_guess = os.path.join(self.source_folder, "config.guess")
        if os.path.exists(config_guess):
            with open(config_guess, "r") as f:
                content = f.read()
            if "HarmonyOS" not in content:
                content = content.replace(
                    "Linux|GNU|GNU/*)",
                    "Linux|GNU|GNU/*|HarmonyOS)",
                )
                content = content.replace(
                    "    aarch64:Linux:*:*)",
                    "    aarch64:Linux:*:* | aarch64:HarmonyOS:*:*)",
                )
                with open(config_guess, "w") as f:
                    f.write(content)

        # Patch configure to fix HMDFS umask 077 permission issue
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(configure_path, "w") as f:
                f.write(content)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        # Create a pkg-config file so other packages can find the encodings dir
        pkgconfig_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        os.makedirs(pkgconfig_dir, exist_ok=True)
        pc_content = (
            "prefix=${pcfiledir}/../..\n"
            "encodingsdir=${prefix}/share/fonts/X11/encodings\n"
            "\n"
            "Name: fonts-encodings\n"
            "Description: X.Org font encoding data files\n"
            "Version: 1.1.0\n"
        )
        with open(os.path.join(pkgconfig_dir, "fonts-encodings.pc"), "w") as f:
            f.write(pc_content)

    def package_info(self):
        # Data-only package: no libraries to link
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
        # pkg-config file provides encodingsdir variable
        self.cpp_info.set_property("pkg_config_name", "fonts-encodings")
