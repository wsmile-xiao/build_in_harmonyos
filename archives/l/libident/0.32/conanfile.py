#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Libident, libident, 0.32, libident 0.32, MIT,
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibidentConan(ConanFile):
    name = "libident"
    version = "0.32"
    description = "libident 0.32"
    license = "LicenseRef-Homebrew-public-domain"
    homepage = "https://www.remlab.net/files/libident/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # Use curl -kL to bypass SSL certificate issues on HarmonyOS
        import subprocess, hashlib, tarfile, tempfile, os, shutil, glob
        src_data = self.conan_data["sources"]
        url = src_data["url"]
        expected_sha256 = src_data["sha256"]
        download_dir = tempfile.mkdtemp()
        tarball = os.path.join(download_dir, os.path.basename(url))
        subprocess.run(["curl", "-kL", "-o", tarball, url], check=True)
        actual_sha256 = hashlib.sha256(open(tarball, "rb").read()).hexdigest()
        if actual_sha256 != expected_sha256:
            raise Exception(f"SHA256 mismatch: expected {expected_sha256}, got {actual_sha256}")
        with tarfile.open(tarball, "r:gz") as tar:
            tar.extractall(path=self.source_folder)
        # Promote nested source dir if needed (strip_root equivalent)
        nested = glob.glob(os.path.join(self.source_folder, "libident-*"))
        if nested and len(nested) == 1:
            nested_dir = nested[0]
            for item in os.listdir(nested_dir):
                src = os.path.join(nested_dir, item)
                dst = os.path.join(self.source_folder, item)
                if os.path.exists(dst):
                    if os.path.isdir(dst):
                        shutil.rmtree(dst)
                    else:
                        os.remove(dst)
                shutil.move(src, dst)
            os.rmdir(nested_dir)
        # Clean up temp dir
        shutil.rmtree(download_dir, ignore_errors=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Static linking configuration for library packages
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix config.guess: umask 077 -> 022 (HMDFS permission issue) + add HarmonyOS support
        import os, re
        cg = os.path.join(self.source_folder, "admin", "config.guess")
        if os.path.exists(cg):
            txt = open(cg).read()
            txt = txt.replace("umask 077", "umask 022")
            if "HarmonyOS" not in txt:
                txt = txt.replace(
                    "    *:DRAGONFLY:*:*)\n\techo ${UNAME_MACHINE}-unknown-dragonfly${UNAME_RELEASE}\n\texit 0 ;;\nesac",
                    "    *:DRAGONFLY:*:*)\n\techo ${UNAME_MACHINE}-unknown-dragonfly${UNAME_RELEASE}\n\texit 0 ;;\n    *:HarmonyOS:*:*)\n\techo ${UNAME_MACHINE}-unknown-linux-gnu\n\texit 0 ;;\nesac"
                )
            open(cg, "w").write(txt)
            os.chmod(cg, 0o755)
        # Fix configure: umask 077 -> 022 in generated config.status
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
        self.cpp_info.libs = ["ident"]
