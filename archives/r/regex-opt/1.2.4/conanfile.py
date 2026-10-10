#!/usr/bin/env python3
"""Conan recipe - regex-opt 1.2.4 (raw Makefile, C++14 regex optimizer).

regex-opt (Bisqwit / Joel Yliluoma) is a Perl-compatible regular expression
optimizer: it reads a regexp and prints an equivalent, optimized regexp
(e.g. `xaz|xbz|xcz` -> `x[a-c]z`).  It ships as a single executable built
from main.cc + libregex.cc (libregex.a) plus a self-contained public header
libregex.hh exposing RegexOptParse()/DumpRegexOptTree().

HarmonyOS PC (aarch64) build notes:
  * Pure Makefile (no configure/autoreconf), so make runs directly in the
    source tree.  Compiler + flags come from the Conan toolchain/profiles,
    never from shell env vars (R33: ${CC}/${CXX} are empty on CI workers).
  * Upstream has NO test framework (audited: no test/ dir, no make check
    target) - see test_package/MANIFEST.yml upstream_test_audit.
  * E077: OHOS refuses to exec an ELF without a .codesign/.note.ohos
    section; package() signs bin/regex-opt and the test_package consumer
    executable with binary-sign-tool before they are executed.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class RegexOptConan(ConanFile):
    name = "regex-opt"
    version = "1.2.4"
    description = ("Perl-compatible regular expression optimizer "
                   "(Bisqwit)")
    license = "GPL-2.0-only"
    homepage = "https://bisqwit.iki.fi/source/regexopt.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("regex", "optimizer", "perl", "code-generation")

    # A command-line tool: packages the executable (and a static helper
    # library for API consumers).  Application package type (R38 tool).
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        # conandata.yml declares an empty patch set; this hook keeps the
        # recipe template-complete (G1).
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # -- helpers -----------------------------------------------------

    def _compiler(self, lang):
        """Prefer the profile's absolute compiler path (R33)."""
        execs = self.conf.get("tools.build:compiler_executables") or {}
        return execs.get(lang) or lang

    def _has_ohos_signature(self, path):
        try:
            with open(path, "rb") as binary:
                data = binary.read()
        except OSError:
            return False
        return b".codesign" in data or b".note.ohos" in data

    def _sign_elf_if_ohos(self, path):
        """Four-step OHOS post-install sign flow (E077), same order as
        re-flex: copy -> llvm-objcopy --remove-section .codesign
        (best-effort) -> binary-sign-tool sign -selfSign 1 -> move back
        -> chmod 755."""
        if not os.path.isfile(path):
            return
        if self._has_ohos_signature(path):
            os.chmod(path, 0o755)
            return
        signer = (
            shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        objcopy = (
            shutil.which("llvm-objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        if not os.path.isfile(signer) or not os.path.isfile(objcopy):
            raise ConanException(
                "OHOS packaging requires binary-sign-tool and llvm-objcopy")
        tmp_in = "{0}.unsigned".format(path)
        tmp_out = "{0}.signed".format(path)
        shutil.copy2(path, tmp_in)
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", tmp_in],
            capture_output=True,
            timeout=30,
        )
        subprocess.check_call([
            signer, "sign", "-selfSign", "1",
            "-inFile", tmp_in, "-outFile", tmp_out,
            "-signAlg", "SHA256withECDSA",
        ])
        shutil.move(tmp_out, path)
        os.chmod(path, 0o755)
        if os.path.isfile(tmp_in):
            os.unlink(tmp_in)

    # -- build ---------------------------------------------------------

    def build(self):
        apply_conandata_patches(self)
        cxx = self._compiler("cpp")
        # Override CC/CPP/CXX + CXXFLAGS so the profile's compiler (never a
        # bare `gcc`, which is absent from the OHOS worker PATH) and a fixed
        # C++ standard win over Makefile.sets defaults (-pedantic -ffast-math
        # ... -std=c++1y).  depfun.mak regenerates .depend via $(CPP) -MM,
        # so CPP must point at the toolchain compiler too.  Raw Makefile
        # builds upstream targets `all` (main.o + libregex.a + `regex-opt`);
        # -j1 per R9.
        self.run(
            "make CC='{0}' CPP='{0}' CXX='{0}' "
            "CXXFLAGS='-std=gnu++17 -O2' LDFLAGS='' -j1".format(cxx)
        )

    def package(self):
        # Tool -> bin/: packaged executable (OHOS-signed, E077).
        copy(self, "regex-opt",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        # Library side: static lib + public header for API consumers.
        copy(self, "libregex.a",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libregex.hh",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # E077: sign the packaged executable (restore +x after signing).
        self._sign_elf_if_ohos(
            os.path.join(self.package_folder, "bin", "regex-opt"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # The helper static library built alongside the tool.
        self.cpp_info.libs = ["regex"]
