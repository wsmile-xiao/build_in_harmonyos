#!/usr/bin/env python3
"""Conan recipe for xvidcore 1.3.7 — MPEG-4 video codec library.

xvidcore uses a custom autotools-based build system with a nested
directory structure (build/generic/ contains the build files, ../../src/
contains the sources). This recipe handles the OHOS platform adaptation.
"""
import os
import re

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class XvidcoreConan(ConanFile):
    name = "xvidcore"
    version = "1.3.7"
    description = "Xvid MPEG-4 video codec library"
    license = "GPL-2.0-or-later"
    homepage = "https://www.xvid.com"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # xvidcore's build files are in build/generic/
        build_dir = os.path.join(self.source_folder, "build", "generic")

        # Determine the host triplet for OHOS
        host_triplet = "aarch64-unknown-linux-ohos"

        # Run configure — it generates config.status which may fail on HMDFS
        # due to mktemp -d "./confXXXXXX" (temp dir creation issue).
        # We catch the failure, fix config.status, and re-run it.
        configure_cmd = (
            f"cd {build_dir} && "
            f"./configure --prefix={self.package_folder} "
            f"--build={host_triplet} --host={host_triplet}"
        )
        # configure may exit non-zero if config.status fails on HMDFS,
        # but config.status is already generated at that point
        try:
            self.run(configure_cmd, env="conanbuild")
        except Exception:
            pass  # Expected: config.status fails on HMDFS, we fix it below

        # Fix config.status: replace mktemp -d "./confXXXXXX" with a
        # pre-created writable directory under TMPDIR.
        config_status_path = os.path.join(build_dir, "config.status")
        if os.path.exists(config_status_path):
            with open(config_status_path, "r") as f:
                content = f.read()

            tmp_work = os.path.join(
                os.environ.get("TMPDIR", os.path.expanduser("~/tmp")),
                "xvidcs_config"
            )
            os.makedirs(tmp_work, exist_ok=True)

            # Replace the mktemp-based tmp assignment with our pre-created dir
            content = re.sub(
                r'tmp=`\(umask 077 && mktemp -d "\./confXXXXXX"\).*`.*;',
                f'tmp={tmp_work};',
                content,
                count=1
            )
            content = content.replace('ac_tmp=$tmp', f'ac_tmp={tmp_work}')

            with open(config_status_path, "w") as f:
                f.write(content)

            # Re-run config.status to generate platform.inc
            self.run(f"cd {build_dir} && ./config.status", env="conanbuild")

        # Build
        self.run(f"cd {build_dir} && make -j1", env="conanbuild")

        # Install
        self.run(f"cd {build_dir} && make install", env="conanbuild")

    def package(self):
        # xvidcore's Makefile installs both static and shared libs to the prefix.
        # We need to keep only the requested type.
        lib_dir = os.path.join(self.package_folder, "lib")

        if not self.options.shared:
            # Remove shared library files, keep only static
            for f in os.listdir(lib_dir) if os.path.exists(lib_dir) else []:
                if ".so" in f:
                    os.remove(os.path.join(lib_dir, f))
        else:
            # Remove static library, keep only shared
            static_lib = os.path.join(lib_dir, "libxvidcore.a")
            if os.path.exists(static_lib):
                os.remove(static_lib)
            # Ensure symlinks exist for shared lib
            so_file = os.path.join(lib_dir, "libxvidcore.so.4.3")
            if os.path.exists(so_file):
                so_major = os.path.join(lib_dir, "libxvidcore.so.4")
                so_link = os.path.join(lib_dir, "libxvidcore.so")
                if not os.path.exists(so_major):
                    os.symlink("libxvidcore.so.4.3", so_major)
                if not os.path.exists(so_link):
                    os.symlink("libxvidcore.so.4.3", so_link)

    def package_info(self):
        self.cpp_info.libs = ["xvidcore"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "m"]
