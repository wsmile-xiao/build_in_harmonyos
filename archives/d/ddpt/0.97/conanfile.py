#!/usr/bin/env python3
"""Conan recipe — ddpt 0.97 (autotools).

ddpt is a dd clone for copying data between files, block devices and
sg/passthrough devices (part of the sg3-utils family). The release tarball
ships a working configure script; the recipe builds it with Conan's
AutotoolsToolchain, which derives the config.guess/config.sub triplet
(--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos,
R32-compatible) from the Conan profiles.

Patches (all knowledge-backed, see patches/ and conandata.yml):
  - 0001/0002 patch config.guess/config.sub for OHOS (E007/E072/E122):
    config.guess learns the HarmonyOS uname branch, config.sub maps
    ohos-linux and accepts ohos* in the OS and kernel-os validation lists
    (this tarball's config.sub 2020-11-19 predates OHOS support).
  - 0003 replaces the `umask 077` wrappers in configure with `umask 022`
    (E011): HMDFS UID mapping makes 0700 temp directories unwritable for
    the current process, so config.status dies with
    "can't create ./confXXXX/subs1.awk: Permission denied".

OHOS notes:
  - No third-party dependencies; the tool links against libc only.
  - The upstream testing/ scripts need real SCSI/ram block devices
    (/dev/sg*, /dev/ram*) and write to /tmp (read-only on OHOS, E002),
    so they are not executable here; the consumer test drives the
    installed binary through regular-file copies instead, which need
    no privileges.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class DdptConan(ConanFile):
    name = "ddpt"
    version = "0.97"
    description = "dd clone for copying data between files and block/sg devices, with SCSI-specific extras"
    license = "BSD-3-Clause"
    homepage = "https://sg.danny.cz/sg/ddpt.html"
    url = "https://sg.danny.cz/sg/ddpt.html"
    topics = ("dd", "copy", "scsi", "block-device", "storage")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ddpt depends on libc only — no third-party dependencies.
        pass

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ddpt supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        # In-source layout (same as the merged cliquer recipe): configure and
        # make run in the source folder, which avoids the separate build dir
        # failing getcwd() on HMDFS right after creation.
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsToolchain provides the CC/CFLAGS/LDFLAGS environment for
        # the configure/make invocations in build(). The --build/--host
        # triplet is passed explicitly on the ./configure command line (see
        # the comment in build()).
        AutotoolsToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # The ohos-aarch64 profile buildenv exports CONFIG_SHELL pointing at
        # the hnp bash, and configure re-execs itself under it; that bash's
        # getcwd() is denied (EPERM) on HMDFS, so autoconf aborts with
        # "working directory cannot be determined". Unset it so configure
        # runs under /bin/sh. AutotoolsToolchain's CC/CFLAGS/LDFLAGS env
        # still applies to every self.run().
        self.run(
            'unset CONFIG_SHELL && ./configure --prefix=/ '
            '--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos',
            cwd=self.source_folder,
        )
        self.run('make -j1', cwd=self.source_folder)

    def package(self):
        self.run(
            'make install DESTDIR="{}"'.format(self.package_folder),
            cwd=self.source_folder,
        )
        # R21/E011-adjacent hygiene: libtool archives bake in absolute
        # libdir paths and break downstream libtool consumers.
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # HarmonyOS XPM requires signed executables; sign the installed binary
        # in place. The hnp tools resolve libc++ via their own location, so the
        # environment must not carry an LD_LIBRARY_PATH pointing at SDK/llvm
        # libs (the ohos-aarch64 profile buildenv prepends them) — hence
        # `env -u LD_LIBRARY_PATH`.
        if self.settings.os != "OHOS":
            return
        targets = []
        for sub in ("bin", "sbin"):
            targets.extend(glob.glob(os.path.join(self.package_folder, sub, "*")))
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if not os.path.isfile(f) or os.path.islink(f) or not self._is_elf(f):
                continue
            # Binaries without an existing .codesign section make objcopy
            # fail; stripping it is optional, hence `|| true`.
            self.run('env -u LD_LIBRARY_PATH {oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('env -u LD_LIBRARY_PATH {sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = []  # ddpt is a CLI tool, it ships no library
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
