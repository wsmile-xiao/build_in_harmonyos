#!/usr/bin/env python3
"""Conan recipe — cccc 3.2.0

CCCC is a code counter for C and C++: it parses sources with a PCCTS-generated
parser and reports simple structural metrics as HTML/XML/database reports
(upstream sarnold/cccc, commit f3b6427 pinned as version 3.2.0 per the
CHANGELOG). Build system: plain recursive Makefiles whose tool variables are
all `?=` defined, so the recipe drives make with clang overrides; the upstream
`all` target also builds and runs the bundled self-test suite. The packaged
CLI binary is signed for OHOS execution (E077). License: the distribution is
a compilation — see licenses/ (upstream LICENSE, GPL-2.0-or-later terms for
the cccc sources per upstream COPYING statements).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class CcccConan(ConanFile):
    name = "cccc"
    version = "3.2.0"
    description = "CCCC — C and C++ Code Counter: structural metrics reports for C/C++ sources"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/sarnold/cccc"
    url = "https://github.com/sarnold/cccc"

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
        # Upstream Makefile defines every tool variable with `?=`, so clang
        # overrides land cleanly: CC for the legacy PCCTS C sources, CCC/LD
        # for the C++ counter itself. `all` = mini (PCCTS tools) + cccc
        # (parser generation and counter build) + test (upstream self-test
        # suite, executed so CI carries real upstream evidence).
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        cxx = comp_execs.get("cpp") or "clang++"
        self.run(f'make -j1 all CC="{cc}" CCC="{cxx}" LD="{cxx}" CPP="cpp -E"', cwd=self.source_folder)

    def package(self):
        copy(self, "cccc", src=os.path.join(self.source_folder, "cccc"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        self._sign_ohos_binary(os.path.join(self.package_folder, "bin", "cccc"))

    def package_info(self):
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
        signer_env = {k: v for k, v in os.environ.items() if k != "LD_LIBRARY_PATH"}
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            capture_output=True, timeout=60, env=signer_env,
        )
        signed = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"],
            check=True, timeout=60, env=signer_env,
        )
        os.chmod(signed, 0o755)
        os.replace(signed, path)
