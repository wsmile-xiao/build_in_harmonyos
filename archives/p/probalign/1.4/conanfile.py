#!/usr/bin/env python3
"""Conan recipe for probalign 1.4.

probalign aligns multiple protein or nucleotide sequences by posterior
probability decoding of a profile hidden Markov model.  Upstream ships a
single raw Makefile: no configure, no install rule, no tests and no
third-party dependencies.  The recipe therefore drives the one upstream
target and performs the install step itself.

R33: the compiler comes from the Conan toolchain conf, never from a shell
variable.  R38: the package is a command line tool, so the software level
``commands.json`` next to this directory declares it.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                               copy, get)
from conan.tools.layout import basic_layout


class ProbalignConan(ConanFile):
    name = "probalign"
    version = "1.4"
    description = (
        "Multiple sequence alignment of protein or nucleotide sequences by "
        "posterior probability decoding of a profile HMM"
    )
    license = "Public-Domain"
    homepage = "https://web.njit.edu/~usman/probalign/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    # The single executable produced by the only upstream Makefile target.
    _binary = "probalign"

    def export_sources(self):
        # conandata.yml declares no patches today; keeping the hook wired means
        # a portability patch added later is exported without touching the
        # recipe again (G1 also requires the export/apply pair).
        export_conandata_patches(self)

    def validate(self):
        # R32: an in-set test rather than an equality test.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "probalign needs a POSIX target (Linux or OHOS)")

    def layout(self):
        basic_layout(self)
        # The upstream Makefile compiles and links in the source directory;
        # there is no out-of-tree support, so build and source share one dir.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        cxx = compilers.get("cpp") or compilers.get("c") or "clang++"

        # Upstream hard-codes `CXX = g++`, which does not exist on the target.
        # A make command-line definition outranks the in-file assignment, so
        # the toolchain is injected without patching the sources.  CXXFLAGS is
        # intentionally left alone: upstream's `-O3 -W -Wall -funroll-loops`
        # compiles clean under clang 15 with warnings only.
        self.run(f'make -j1 CXX="{cxx}"', cwd=self.source_folder)

    def package(self):
        # Upstream has no install rule; mirror the conventional FHS layout.
        copy(self,
             self._binary,
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)
        # README carries the public-domain statement the package is licensed
        # under, RELEASE_NOTES the version provenance.
        for document in ("README", "RELEASE_NOTES"):
            copy(self,
                 document,
                 src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"),
                 keep_path=False)

        binary = os.path.join(self.package_folder, "bin", self._binary)
        if not os.path.isfile(binary):
            raise Exception("probalign executable was not produced")
        os.chmod(binary, 0o755)
        self._sign_ohos_binary(binary)

    def _sign_ohos_binary(self, path):
        """HarmonyOS refuses to exec an unsigned ELF from the Conan cache."""
        if str(self.settings.os) != "OHOS":
            return

        signer = (self.conf.get("user.ohos:sign_tool",
                                default="",
                                check_type=str)
                  or os.environ.get("OHOS_SIGN_TOOL", "")
                  or shutil.which("binary-sign-tool")
                  or "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool is unavailable; skipping OHOS ELF signing")
            return

        objcopy = (self.conf.get("user.ohos:objcopy",
                                 default="",
                                 check_type=str)
                   or os.environ.get("OHOS_OBJCOPY", "")
                   or shutil.which("llvm-objcopy")
                   or "/data/service/hnp/bin/llvm-objcopy")
        if os.path.isfile(objcopy):
            # A re-signed binary must not accumulate stale .codesign data.
            self.run(f'"{objcopy}" --remove-section .codesign "{path}"',
                     ignore_errors=True)

        signed = f"{path}.signed"
        self.run(f'"{signer}" sign -inFile "{path}" '
                 f'-outFile "{signed}" -selfSign 1')
        if not os.path.isfile(signed):
            raise Exception(f"binary-sign-tool produced no output for {path}")
        os.replace(signed, path)
        # The signer may rewrite the file, so restore the exec bit after it.
        os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
