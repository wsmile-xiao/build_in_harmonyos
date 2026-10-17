#!/usr/bin/env python3
"""Conan recipe for bmd-tools v1.0.2 — Blackmagic Design USB H.264 tools.

bmd-tools provides two command-line tools:
  - bmd-streamer:  USB H.264 video streaming tool
  - bmd-extractfw: Firmware extraction tool

Build: simple Makefile using pkg-config for libusb-1.0
Deps:  libusb/1.0.27 (Conan artifact repo)

The Makefile calls pkg-config to find libusb-1.0, but CI workers
may not have .pc files. We bypass pkg-config by passing flags directly
as make command-line variables (PKG_CONFIG=true disables shell calls).
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BmdToolsConan(ConanFile):
    name = "bmd-tools"
    version = "v1.0.2"
    description = "Blackmagic Design USB H.264 streaming and firmware extraction tools"
    license = "GPL-2.0"
    homepage = "https://github.com/fabled/bmd-tools"
    url = "https://github.com/fabled/bmd-tools"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libusb/1.0.27")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"

        # Get libusb flags from Conan dependency metadata.
        libusb = self.dependencies["libusb"].cpp_info
        libusb_cflags = " ".join(f"-I{d}" for d in libusb.includedirs)
        libusb_libs = " ".join(
            [*(f"-L{d}" for d in libusb.libdirs),
             *(f"-l{name}" for name in libusb.libs)]
        )
        system_libs = " ".join(f"-l{name}" for name in libusb.system_libs)
        libusb_ldflags = f"{libusb_libs} {system_libs}".strip()

        self.output.info(f"libusb cflags: {libusb_cflags}")
        self.output.info(f"libusb ldflags: {libusb_ldflags}")

        # Bypass pkg-config: set PKG_CONFIG=true so shell calls return empty.
        # Command-line vars override Makefile += assignments.
        # Use GNU ld (ld.bfd) to avoid lld's libxml2.so dependency issue on CI.
        # Include ld flag in LIBUSB_LDFLAGS (not LDFLAGS) so the Makefile's
        # target-specific `bmd-streamer: LDFLAGS+=$(LIBUSB_LDFLAGS) ...` works.
        ld_bfd = "/data/service/hnp/bin/ld.bfd"
        ld_flag = f"-fuse-ld={ld_bfd} " if os.path.isfile(ld_bfd) else ""
        libusb_ldflags = f"{ld_flag}{libusb_libs} {system_libs}".strip()
        self.run(
            f'make -C {self.source_folder} CC="{cc}" -j1 '
            f'PKG_CONFIG=true '
            f'LIBUSB_CFLAGS="{libusb_cflags}" '
            f'LIBUSB_LDFLAGS="{libusb_ldflags}"'
        )

    def package(self):
        # Copy executables to bin/
        copy(self, "bmd-streamer", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "bmd-extractfw", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # Sign ELF binaries for HarmonyOS (R38/E082)
        for name in ("bmd-streamer", "bmd-extractfw"):
            path = os.path.join(self.package_folder, "bin", name)
            if os.path.exists(path):
                os.chmod(path, 0o755)
                self._sign_elf(path)

    def _sign_elf(self, path):
        """Sign an ELF binary for HarmonyOS execution."""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(sign_tool) and os.path.isfile(objcopy)):
            self.output.warning("ELF signing tools not found; skipping.")
            return
        try:
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", path],
                check=False, capture_output=True, timeout=10,
            )
        except subprocess.TimeoutExpired:
            self.output.warning(f"ELF objcopy timed out for {os.path.basename(path)}; skipping signing.")
            return
        tmp = path + ".signed"
        try:
            r = subprocess.run(
                [sign_tool, "sign", "-inFile", path, "-outFile", tmp, "-selfSign", "1"],
                capture_output=True, text=True, timeout=30,
            )
        except subprocess.TimeoutExpired:
            self.output.warning(f"ELF signing timed out for {os.path.basename(path)}; skipping.")
            return
        if r.returncode == 0 and os.path.exists(tmp):
            os.replace(tmp, path)
            os.chmod(path, 0o755)
        else:
            self.output.warning(
                f"ELF signing failed for {os.path.basename(path)}: {r.stderr}"
            )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
