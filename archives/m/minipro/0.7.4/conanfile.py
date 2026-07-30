#!/usr/bin/env python3
"""Conan recipe for minipro 0.7.4 — XGecu chip programmer control tool.

Minipro is an open source command-line program for controlling XGecu's
series of chip programmers (TL866CS, TL866A, TL866II+, T48, T56).

Build: make → minipro (single binary, plain Makefile with pkg-config deps)
Deps:  libusb-1.0 (verified cmd-pkgs archive), zlib/1.3.1 (Conan)

The Makefile calls pkg-config to find libusb-1.0 and zlib, but CI workers
install these as system packages WITHOUT .pc files. We bypass pkg-config
entirely by passing the flags directly as make command-line variables
(command-line vars override := assignments in GNU Make).

See: https://gitlab.com/DavidGriffith/minipro
"""
import os
import subprocess
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class MiniproConan(ConanFile):
    name = "minipro"
    version = "0.7.4"
    description = "Open source program for controlling XGecu chip programmers"
    license = "GPL-3.0"
    homepage = "https://gitlab.com/DavidGriffith/minipro"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _libusb_prefix(self):
        extract_dir = os.path.join(self.build_folder, "libusb")
        prefix = extract_dir
        header = os.path.join(prefix, "include", "libusb-1.0", "libusb.h")
        library = os.path.join(prefix, "lib", "libusb-1.0.a")
        if os.path.isfile(header) and os.path.isfile(library):
            return prefix
        os.makedirs(extract_dir, exist_ok=True)
        get(self, **self.conan_data["libusb"], destination=extract_dir, strip_root=True)
        if not os.path.isfile(header) or not os.path.isfile(library):
            raise RuntimeError("libusb cmd-pkgs archive is missing headers or static library")
        return prefix

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"

        zlib = self.dependencies["zlib"].cpp_info
        libusb_prefix = self._libusb_prefix()
        libusb_cflags = f"-I{libusb_prefix}/include/libusb-1.0"
        libusb_libs = f"{libusb_prefix}/lib/libusb-1.0.a -lpthread"
        zlib_cflags = " ".join(f"-I{path}" for path in zlib.includedirs)
        zlib_libs = " ".join(
            [*(f"-L{path}" for path in zlib.libdirs),
             *(f"-l{name}" for name in zlib.libs)]
        )

        self.output.info("Bypassing pkg-config with Conan dependency metadata")
        self.output.info(f"  libusb: cflags={libusb_cflags} libs={libusb_libs}")
        self.output.info(f"  zlib:   cflags={zlib_cflags} libs={zlib_libs}")

        # R9: Always use -j1 for reproducible builds.
        self.run(
            f'make -C {self.source_folder} CC="{cc}" -j1 '
            f'libusb_CFLAGS="{libusb_cflags}" libusb_LIBS="{libusb_libs}" '
            f'zlib_CFLAGS="{zlib_cflags}" zlib_LIBS="{zlib_libs}"'
        )

    def package(self):
        # Binary
        copy(self, "minipro", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        # Man page
        copy(self, "minipro.1", src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        # Data files (chip database)
        copy(self, "infoic.xml", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "minipro"))
        copy(self, "logicic.xml", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "minipro"))

        # R38/E082: HarmonyOS requires ELF signing before a binary can execute.
        bin_path = os.path.join(self.package_folder, "bin", "minipro")
        if os.path.exists(bin_path) and self.settings.os in ("Linux", "OHOS"):
            self._sign_elf(bin_path)

    def _sign_elf(self, path):
        """Sign an ELF binary for HarmonyOS execution (R38/E082)."""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(sign_tool) and os.path.isfile(objcopy)):
            self.output.warning("ELF signing tools not found; skipping (CI worker will sign).")
            return
        # Remove any existing .codesign section (may not exist on fresh build).
        objcopy_result = subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            check=False, capture_output=True, text=True, timeout=10,
        )
        if objcopy_result.returncode != 0:
            detail = (objcopy_result.stderr or objcopy_result.stdout).strip()
            self.output.warning(
                f"Failed to remove .codesign section (rc={objcopy_result.returncode}): {detail}"
            )
        tmp = path + ".signed.tmp"
        r = subprocess.run(
            [sign_tool, "sign", "-inFile", path, "-outFile", tmp, "-selfSign", "1"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0 and os.path.exists(tmp):
            os.replace(tmp, path)
            os.chmod(path, 0o755)
        else:
            detail = (r.stderr or r.stdout).strip()
            raise RuntimeError(
                f"ELF signing failed for {os.path.basename(path)} "
                f"(rc={r.returncode}): {detail}"
            )

    def package_info(self):
        # Application — no libraries, just a binary in bin/
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
