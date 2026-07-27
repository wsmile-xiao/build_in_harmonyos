#!/usr/bin/env python3
"""Conan recipe — rpm2cpio 1.4-r3 (makefile)

Shell script tool that converts RPM packages to cpio archives.
Source: FreeBSD ports (archivers/rpm2cpio). No C/C++ compilation needed.
"""
import os

from conan import ConanFile
from conan.tools.files import download, copy, apply_conandata_patches, export_conandata_patches


class Rpm2CpioConan(ConanFile):
    name = "rpm2cpio"
    version = "1.4-r3"
    description = "Convert RPM packages to cpio archives (shell script)"
    license = "BSD-2-Clause"
    homepage = "https://cgit.freebsd.org/ports/tree/archivers/rpm2cpio"

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # Download raw shell script (not a tarball)
        download(self, **self.conan_data["sources"], filename="rpm2cpio.sh")

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        # Install the script and symlink to package bin directory
        target_bin = os.path.join(self.package_folder, "bin")
        os.makedirs(target_bin, exist_ok=True)
        # Copy and rename the script
        copy(self, "rpm2cpio.sh", self.source_folder, target_bin)
        src_script = os.path.join(target_bin, "rpm2cpio.sh")
        dst_script = os.path.join(target_bin, "rpm2cpio")
        if os.path.exists(dst_script):
            os.remove(dst_script)
        os.rename(src_script, dst_script)
        # Ensure the script is executable
        os.chmod(dst_script, 0o755)
        # Create symlink (R5: use rm -f && ln -s)
        symlink_path = os.path.join(target_bin, "rpm2cpio.pl")
        if os.path.exists(symlink_path) or os.path.islink(symlink_path):
            os.remove(symlink_path)
        os.symlink("rpm2cpio", symlink_path)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
