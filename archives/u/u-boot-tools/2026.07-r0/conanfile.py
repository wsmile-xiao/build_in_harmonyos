#!/usr/bin/env python3
"""Conan recipe — u-boot-tools 2026.07-r0

Builds the U-Boot host tools (mkimage, dumpimage, mkenvimage, fdtgrep, etc.)
from the main U-Boot source tree using the 'tools-only' target.

Build system: custom Makefile (not autotools, not CMake).
U-Boot tools are host-side utilities extracted from the full U-Boot bootloader.
License: GPL-2.0+
"""
import hashlib
import os
import tarfile

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class UbootToolsConan(ConanFile):
    name = "u-boot-tools"
    version = "2026.07-r0"
    description = "U-Boot bootloader host tools (mkimage, dumpimage, mkenvimage, fdtgrep, etc.)"
    license = "GPL-2.0+"
    homepage = "https://github.com/u-boot/u-boot"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # R26: u-boot-tools are host-side tools with no system-name library collision risk.
    # R38: This package produces CLI executables (mkimage, dumpimage, etc.).

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Build a self-contained host tools subset without external libraries.
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        local_tarball = os.environ.get("U_BOOT_TOOLS_TARBALL")
        expected_sha256 = self.conan_data["sources"]["sha256"]
        if local_tarball and os.path.isfile(local_tarball):
            with open(local_tarball, "rb") as f:
                actual_sha256 = hashlib.sha256(f.read()).hexdigest()
            if actual_sha256 == expected_sha256:
                self.output.info(f"Using pre-downloaded source tarball: {local_tarball}")
                with tarfile.open(local_tarball, "r:bz2") as tf:
                    try:
                        tf.extractall(self.source_folder, filter="data")
                    except TypeError:
                        tf.extractall(self.source_folder)
                entries = [e for e in os.listdir(self.source_folder) if e not in ("conandata.yml", "conanfile.py")]
                if len(entries) == 1 and os.path.isdir(os.path.join(self.source_folder, entries[0])):
                    root = os.path.join(self.source_folder, entries[0])
                    for name in os.listdir(root):
                        os.replace(os.path.join(root, name), os.path.join(self.source_folder, name))
                    os.rmdir(root)
                return

        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        compiler_executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compiler_executables.get("c") or "clang"

        # Step 1: Configure a minimal host-tools-capable build.
        # U-Boot v2026.07 provides tools-only as a build target, but not a
        # tools-only_defconfig configuration target; sandbox_defconfig is the
        # upstream host-build configuration used for tooling builds.
        make_base = f"make -C {self.source_folder} O={self.build_folder} CC={cc} HOSTCC={cc} HOSTLD={cc}"
        self.run(f"{make_base} sandbox_defconfig -j1")

        # The sandbox default enables FIT signing/cipher tooling, which requires
        # OpenSSL headers not available as a published ohpcd/stable dependency.
        # Disable those optional features to keep the CLI tools package self-contained.
        config_tool = os.path.join(self.source_folder, "scripts", "config")
        config_file = os.path.join(self.build_folder, ".config")
        disabled_configs = " ".join(
            f"--disable {name}" for name in [
                "FIT_SIGNATURE",
                "FIT_CIPHER",
                "TOOLS_KWBIMAGE",
                "TOOLS_LIBCRYPTO",
                "TOOLS_FIT_SIGNATURE",
                "TOOLS_RSASSA_PSS",
                "TOOLS_MKEFICAPSULE",
            ]
        )
        self.run(f"{config_tool} --file {config_file} {disabled_configs}")
        self.run(f"{make_base} olddefconfig -j1")

        # Step 2: Build host tools through the upstream-supported aggregate target.
        # Direct tools/<name> targets do not work with U-Boot's O= out-of-tree
        # build because some recursive rules resolve them as /tools/.
        # R9: Always use -j1 to avoid jobserver fifo issues on OHOS/HMDFS.
        self.run(f"{make_base} tools-only HOSTCC={cc} HOSTLDSHARED='{cc} -shared' -j1")

    def package(self):
        # The tools are built in the tools/ subdirectory.
        tools_dir = os.path.join(self.build_folder, "tools")
        bin_dir = os.path.join(self.package_folder, "bin")

        # List of known host tools built by tools-only target
        tool_names = [
            "mkimage",
            "dumpimage",
            "mkenvimage",
            "fdtgrep",
            "fit_info",
            "fit_check_sign",
            "envcrc",
            "gen_eth_addr",
            "gen_ethaddr_crc",
            "fdt_add_pubkey",
            "file2include",
            "img2srec",
            "bmp_logo",
            "proftool",
            "spl_size_limit",
            "ifdtool",
            "ifwitool",
        ]

        os.makedirs(bin_dir, exist_ok=True)
        for tool in tool_names:
            tool_path = os.path.join(tools_dir, tool)
            if os.path.isfile(tool_path) and os.access(tool_path, os.X_OK):
                copy(self, tool, src=tools_dir, dst=bin_dir)
                self.output.info(f"Packaged: {tool}")

        # Do not auto-package every executable in tools/: some U-Boot helper
        # binaries (for example ncb) are build-time helpers and may block on
        # generic --version probes in local CI.

        # Copy license file
        license_src = os.path.join(self.source_folder, "Licenses", "gpl-2.0.txt")
        if os.path.isfile(license_src):
            copy(self, "gpl-2.0.txt", src=os.path.dirname(license_src),
                 dst=os.path.join(self.package_folder, "share", "licenses", self.name))

    def package_info(self):
        # u-boot-tools provides CLI executables, not libraries.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
