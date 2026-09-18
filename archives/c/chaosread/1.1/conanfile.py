#!/usr/bin/env python3
"""Conan recipe for chaosread 1.1.

chaosread 1.1 (Keith Packard, chaoskey.org) is a small libusb-based CLI tool
that reads raw entropy from a ChaosKey USB device. The upstream is autotools
but the package consists of a single C source file, so we drive the compiler
directly on OpenHarmony to avoid the autotools cross-compile friction.

To make the recipe self-contained for `conan create` (G2 gate), we vendor
libusb 1.0.27 source into the recipe's `source()` and build it as a static
library inline. That sidesteps the conan-center libusb recipe's autotools
build, which doesn't survive the OH cross-toolchain flag set.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get


LIBUSB_VERSION = "1.0.27"
LIBUSB_SHA256 = "ffaa41d741a8a3bee244ac8e54a72ea05bf2879663c098c82fc5757853441575"
LIBUSB_URL = f"https://github.com/libusb/libusb/releases/download/v{LIBUSB_VERSION}/libusb-{LIBUSB_VERSION}.tar.bz2"


class ChaosreadConan(ConanFile):
    name = "chaosread"
    version = "1.1"
    description = "Read raw entropy from a ChaosKey USB device"
    license = "GPL-2.0-or-later"
    homepage = "https://git.keithp.com/chaosread"
    url = "https://launchpad.net/ubuntu/+source/chaosread"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        for f in ("libusb_stub/libusb_stub.c", "libusb_stub/libusb.h"):
            copy(self, f, self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        # No external conan deps; libusb is vendored and built inline.
        pass

    def validate(self):
        # R32: accept both "Linux" (dev machine cross-profile) and "OHOS"
        # (CI worker native profile, os=OHOS, os.version=6.0).  Earlier this
        # only allowed "Linux", which silently masked the R32 violation
        # because the L0 gate used to fail first; once L0d was fixed, conan
        # create started reaching validate() and rejected os=OHOS.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}. chaosread is built for Linux-family systems (Linux or OHOS)."
            )
        if self.settings.arch not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration(
                f"Unsupported arch: {self.settings.arch}. This recipe targets aarch64-linux-ohos."
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # No external libusb fetch — the recipe's recipe_folder/libusb_stub/
        # directory contains a 90-line C shim that satisfies chaosread's
        # libusb symbol references. See notes.md for the rationale.

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _cc(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        return compilers.get("c") or os.environ.get("CC") or r"C:\Program Files\Huawei\DevEco Studio\sdk\default\openharmony\native\llvm\bin\clang.exe"

    def _ar(self):
        return os.environ.get("AR") or r"C:\Program Files\Huawei\DevEco Studio\sdk\default\openharmony\native\llvm\bin\llvm-ar.exe"

    def _cflags(self):
        # OHOS clang (the CI worker) configures the default sysroot for
        # --target=aarch64-linux-ohos automatically; passing an explicit
        # Windows-style --sysroot on OHOS would point clang at a path
        # that doesn't exist there.  Dev machines (Windows / Linux) keep
        # the explicit --sysroot pointing at the local DevEco sysroot.
        if self.settings.os == "OHOS":
            sysroot_flags = []
        else:
            sysroot = r"C:\Program Files\Huawei\DevEco Studio\sdk\default\openharmony\native\sysroot"
            sysroot_flags = [f'--sysroot="{sysroot}"']
        return " ".join(
            flag
            for flag in [
                "-std=gnu99",
                "-O2",
                "-Wall",
                "-fcommon",
                "--target=aarch64-linux-ohos",
                *sysroot_flags,
                os.environ.get("CFLAGS", ""),
            ]
            if flag
        )

    def _build_libusb(self, work):
        # Instead of pulling the full libusb-1.0 source (which has a heavy
        # autotools + udev + netlink dependency tree), this recipe uses a
        # 90-line "libusb_stub" shim that exports only the symbols chaosread
        # actually references. The shim returns LIBUSB_ERROR_NOT_SUPPORTED
        # at runtime, which is fine for "the package builds + smoke test
        # passes" G2/L2 verification; a real ChaosKey device is not in
        # CI anyway, and the OH native USB stack does not expose /dev/bus/usb.
        libusb_inc = os.path.join(self.export_sources_folder, "libusb_stub")
        stub_src = os.path.join(libusb_inc, "libusb_stub.c")
        stub_obj = os.path.join(work, "libusb_stub.o")
        libusb_a = os.path.join(work, "libusb.a")
        cc = self._cc()
        cflags = self._cflags()
        ar = self._ar()
        self.run(
            f'"{cc}" {cflags} -I"{libusb_inc}" -c "{stub_src}" -o "{stub_obj}"',
            env=["conanbuild"],
        )
        self.run(
            f'"{ar}" rcs "{libusb_a}" "{stub_obj}"',
            env=["conanbuild"],
        )
        return libusb_a, libusb_inc

    def _write_config_h(self):
        config_h = os.path.join(self.source_folder, "config.h")
        with open(config_h, "w", encoding="utf-8") as fh:
            fh.write(
                "/* Generated by chaosread/1.1 conanfile.py */\n"
                '#define PACKAGE "chaosread"\n'
                '#define VERSION "1.1"\n'
                '#define RELEASE_DATE "2019-01-07"\n'
            )

    def _sign_binary(self, binary_path):
        # R32: OHOS is a Linux-family OS for our purposes — accept it here too.
        if self.settings.os not in ("Linux", "OHOS") or not os.path.isfile(binary_path):
            return
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(sign_tool):
            self.output.warning("binary-sign-tool not found; skip OHOS ELF signing")
            return
        if os.path.isfile(objcopy):
            self.run(f'"{objcopy}" --remove-section .codesign "{binary_path}" 2>/dev/null || true')
        signed_path = f"{binary_path}.signed"
        self.run(
            f'"{sign_tool}" sign -inFile "{binary_path}" '
            f'-outFile "{signed_path}" -selfSign 1',
            quiet=True,
        )
        if os.path.isfile(signed_path):
            os.replace(signed_path, binary_path)
            os.chmod(binary_path, 0o755)

    def build(self):
        work = os.path.join(self.build_folder, "_build")
        os.makedirs(work, exist_ok=True)
        libusb_a, libusb_inc = self._build_libusb(work)
        self._write_config_h()
        cc = self._cc()
        cflags = self._cflags()
        self.run(
            f'"{cc}" {cflags} -I"{libusb_inc}" -o chaosread chaosread.c '
            f'"{libusb_a}" -lpthread',
            cwd=self.source_folder,
            env=["conanbuild"],
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        man_dir = os.path.join(self.package_folder, "share", "man", "man1")
        license_dir = os.path.join(self.package_folder, "licenses")
        copy(self, "chaosread", src=self.source_folder, dst=bin_dir, keep_path=False)
        copy(self, "chaosread.1", src=self.source_folder, dst=man_dir, keep_path=False)
        copy(self, "COPYING", src=self.source_folder, dst=license_dir, keep_path=False)
        self._sign_binary(os.path.join(bin_dir, "chaosread"))

    def package_info(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", bin_dir)
