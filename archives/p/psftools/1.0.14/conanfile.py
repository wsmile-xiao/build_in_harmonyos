#!/usr/bin/env python3
"""Conan recipe for psftools 1.0.14 — Autotools (configure + make).

Tools for fixed-width bitmap fonts (PSF format).
License: GPL-2.0-or-later

This recipe enforces R26: static linking for terminal tools.
"""
import os
import hashlib
import tarfile
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PsftoolsConan(ConanFile):
    name = "psftools"
    version = "1.0.14"
    description = "Tools for fixed-width bitmap fonts (PSF format)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.seasip.info/Unix/PSF/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # Use curl -kL to download (SSL workaround for HarmonyOS)
        url = self.conan_data["sources"]["url"]
        expected_sha256 = self.conan_data["sources"]["sha256"]
        archive_name = "psftools-1.0.14.tar.gz"
        archive_path = os.path.join(self.source_folder, archive_name)
        subprocess.run(["curl", "-kL", "-o", archive_path, url], check=True)
        # Verify sha256
        actual_sha256 = hashlib.sha256(open(archive_path, "rb").read()).hexdigest()
        if actual_sha256 != expected_sha256:
            raise Exception(f"sha256 mismatch: expected={expected_sha256}, got={actual_sha256}")
        # Extract with tarfile
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=self.source_folder)
        # Move extracted content to source folder root
        extracted_dir = os.path.join(self.source_folder, f"psftools-{self.version}")
        for item in os.listdir(extracted_dir):
            src = os.path.join(extracted_dir, item)
            dst = os.path.join(self.source_folder, item)
            if os.path.exists(dst):
                if os.path.isdir(dst):
                    shutil.rmtree(dst)
                else:
                    os.remove(dst)
            shutil.move(src, dst)
        os.rmdir(extracted_dir)
        os.remove(archive_path)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.configure_args.append("--disable-shared")
        tc.extra_ldflags.append("-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix config.guess: add HarmonyOS support + fix umask 077 -> 022 (HMDFS)
        cg = os.path.join(self.source_folder, "config", "config.guess")
        if os.path.exists(cg):
            txt = open(cg).read()
            txt = txt.replace("umask 077", "umask 022")
            if "HarmonyOS" not in txt:
                txt = txt.replace(
                    "    i*86:atheos:*:*)\n\techo ${UNAME_MACHINE}-unknown-atheos\n\texit 0 ;;\nesac",
                    "    i*86:atheos:*:*)\n\techo ${UNAME_MACHINE}-unknown-atheos\n\texit 0 ;;\n    *:HarmonyOS:*:*)\n\techo ${UNAME_MACHINE}-unknown-linux-gnu\n\texit 0 ;;\nesac"
                )
            open(cg, "w").write(txt)
            os.chmod(cg, 0o755)
        cs = os.path.join(self.source_folder, "config", "config.sub")
        if os.path.exists(cs):
            os.chmod(cs, 0o755)
        # Fix configure: umask 077 -> 022 in generated config.status (HMDFS)
        cfg = os.path.join(self.source_folder, "configure")
        if os.path.exists(cfg):
            txt = open(cfg).read()
            txt = txt.replace("umask 077", "umask 022")
            open(cfg, "w").write(txt)
            os.chmod(cfg, 0o755)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["psf"]
