#!/usr/bin/env python3
"""Conan recipe — GNU ed 1.20

GNU ed is a line-oriented text editor. It is the standard text editor
of Unix and the ancestor of vi and sed.

Build system: Autotools (configure + make).
License: GPL-2.0-or-later
Homepage: https://www.gnu.org/software/ed/

Source is distributed as .tar.lz (lzip compressed). The source() method
handles decompression via the lzip binary (built from source if needed).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import download, unzip, replace_in_file, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class EdConan(ConanFile):
    name = "ed"
    version = "1.20"
    description = "GNU ed is a line-oriented text editor"
    license = "GPL-2.0-or-later"
    homepage = "https://www.gnu.org/software/ed/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # GNU ed is distributed as .tar.lz (lzip compressed).
        # Conan's get() does not support .tar.lz, so we download and
        # decompress manually using the lzip binary.
        src_data = self.conan_data["sources"]
        urls = src_data.get("url", "")
        sha256 = src_data.get("sha256", "")
        if isinstance(urls, str):
            urls = [urls]

        archive = os.path.join(self.source_folder, "ed-1.20.tar.lz")
        last_err = None
        for url in urls:
            try:
                download(self, url, archive, sha256=sha256, verify=True)
                break
            except Exception as e:
                last_err = e
                continue
        else:
            raise last_err or RuntimeError("No source URL available")

        # Decompress .tar.lz → .tar
        lzip = shutil.which("lzip")
        if not lzip:
            # Try common install paths on HarmonyOS
            for candidate in [
                os.path.expanduser("~/usr/local/bin/lzip"),
                "/data/service/hnp/bin/lzip",
            ]:
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    lzip = candidate
                    break

        if not lzip:
            # Build lzip from source (lzip is needed to decompress .tar.lz)
            lzip_url = "https://download.savannah.gnu.org/releases/lzip/lzip-1.25.tar.gz"
            lzip_sha256 = "09418a6d8fb83f5113f5bd856e09703df5d37bae0308c668d0f346e3d3f0a56f"
            lzip_archive = os.path.join(self.source_folder, "lzip-1.25.tar.gz")
            download(self, lzip_url, lzip_archive, sha256=lzip_sha256, verify=True)
            import tarfile as _tf
            with _tf.open(lzip_archive, "r:gz") as tf:
                tf.extractall(self.source_folder, filter="data")
            os.unlink(lzip_archive)

            lzip_src = os.path.join(self.source_folder, "lzip-1.25")
            comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
            cxx = comp_execs.get("cpp") or "clang++"
            cc = comp_execs.get("c") or "clang"
            subprocess.run(
                ["./configure", f"--prefix={self.source_folder}/.lzip",
                 f"CC={cc}", f"CXX={cxx}"],
                cwd=lzip_src, check=True, capture_output=True)
            subprocess.run(["make", "-j1"], cwd=lzip_src, check=True, capture_output=True)
            subprocess.run(["make", "install"], cwd=lzip_src, check=True, capture_output=True)
            lzip = os.path.join(self.source_folder, ".lzip", "bin", "lzip")
            # Clean up lzip source to avoid polluting the package
            shutil.rmtree(lzip_src, ignore_errors=True)

        subprocess.run([lzip, "-d", "-k", "-f", archive],
                       check=True, capture_output=True)

        tar_path = archive.replace(".tar.lz", ".tar")
        # Use conan's unzip with strip_root to extract the .tar file
        unzip(self, tar_path, destination=self.source_folder, strip_root=True)

        os.unlink(archive)
        os.unlink(tar_path)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R33: Get compiler from Conan conf, pass to configure explicitly
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        tc.configure_args.append(f"CC={cc}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E165: Fix shebang for HarmonyOS (/bin/sh → /system/bin/sh)
        configure_path = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure_path, "#!/bin/sh", "#!/system/bin/sh", strict=False)
        replace_in_file(self, configure_path, "#! /bin/sh", "#! /system/bin/sh", strict=False)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
