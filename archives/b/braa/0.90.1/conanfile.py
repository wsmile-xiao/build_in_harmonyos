#!/usr/bin/env python3
"""Conan recipe — braa 0.90.1

Mass SNMP scanner — ultra-fast SNMPv1/v2c stack able to get/set/walk tens of
thousands of hosts at once in a single process (upstream mteg/braa).

Build system: plain Makefile with a hardcoded `cc` link rule and a trailing
`strip` — no configure, no install rule — so the recipe drives make directly
and installs the single binary into bin/ itself.
License: GPL-2.0-only (upstream COPYING).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class BraaConan(ConanFile):
    name = "braa"
    version = "0.90.1"
    description = "Mass SNMP scanner — ultra-fast SNMPv1/v2c stack querying tens of thousands of hosts at once"
    license = "GPL-2.0-only"
    homepage = "https://github.com/mteg/braa"
    url = "https://github.com/mteg/braa"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler from Conan conf — upstream Makefile hardcodes `cc`
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        # The Makefile defines CFLAGS/LDFLAGS empty (upstream default, asserts
        # on), but CPPFLAGS is undefined in it and would inherit Conan's
        # Release -DNDEBUG from the environment. queries.c does
        # `assert(string = strdup(string))` — compiling the assert out removes
        # the strdup and segfaults query parsing, so CPPFLAGS is pinned empty
        # to keep the faithful upstream build.
        self.run(f'make -j1 CC="{cc}" CPPFLAGS=', cwd=self.source_folder)

    def package(self):
        # CLI tool with no upstream install rule: install the binary to bin/
        copy(self, "braa", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        self._sign_ohos_binary(os.path.join(self.package_folder, "bin", "braa"))

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

    def _sign_ohos_binary(self, path):
        # OHOS only loads ELF executables carrying a valid .codesign section
        # (E077): the OHOS toolchain embeds an unsigned placeholder that makes
        # the final self-sign fail with ".codesign section already exists", so
        # it must be removed before signing (order is mandatory).
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(path):
            raise ConanException(f"Missing packaged executable: {path}")
        if not os.path.isfile(signer) or not os.path.isfile(objcopy):
            raise ConanException("Required OHOS signing tools are missing")
        # The Conan build env points LD_LIBRARY_PATH at the cross toolchain's
        # runtime libs, whose libc++ shadows the system OHOS libc++ (std::__h)
        # that binary-sign-tool needs — run it with the inherited loader path.
        signer_env = os.environ.copy()
        signer_env.pop("LD_LIBRARY_PATH", None)
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            capture_output=True,
            timeout=60,
            env=signer_env,
        )
        signed = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"],
            check=True,
            timeout=60,
            env=signer_env,
        )
        os.chmod(signed, 0o755)
        os.replace(signed, path)
