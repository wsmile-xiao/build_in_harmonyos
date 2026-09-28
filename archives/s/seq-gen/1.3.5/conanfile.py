#!/usr/bin/env python3
"""Conan recipe for seq-gen 1.3.5 (Seq-Gen, HarmonyOS PC).

Upstream is a raw Makefile project that produces a single command line
executable and has no install rule, so the recipe drives make directly and
installs the binary itself.  Two upstream facts shape this recipe:

1. ``source/Makefile`` hardcodes ``CLINKER = cc`` and ``CFLAGS = -O3``.  On the
   HarmonyOS worker ``cc`` is not the Conan-provided compiler, so both must be
   injected on the make command line (R33: values come from
   ``tools.build:compiler_executables``, never from shell env vars).
2. The release tarball ships a **prebuilt Mach-O arm64 binary** at
   ``source/seq-gen``.  It is removed before building: leaving it in place lets
   make consider the target up to date and would package a foreign-ABI
   artifact that cannot execute on OHOS.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class SeqGenConan(ConanFile):
    name = "seq-gen"
    version = "1.3.5"
    description = (
        "Seq-Gen: Monte Carlo simulation of molecular sequence evolution "
        "(DNA and protein) along phylogenetic trees"
    )
    # Per-file headers: BSD-3-Clause (Rambaut); gamma.c is taken from PAML
    # and states GNU GPL v3.  Upstream ships no top-level LICENSE file.
    license = ("BSD-3-Clause", "GPL-3.0-only")
    homepage = "https://github.com/rambaut/Seq-Gen"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: OHOS must be accepted alongside Linux, never "== Linux".
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"seq-gen supports Linux and OHOS only, got {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True, verify=True)

    def _src_dir(self):
        # The tarball keeps the buildable sources in a source/ subdirectory.
        return os.path.join(self.source_folder, "source")

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get("c") or "clang"

    def _ohos_tool(self, name, default):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get(name, default)

    def build(self):
        apply_conandata_patches(self)
        src = self._src_dir()

        stale = os.path.join(src, "seq-gen")
        if os.path.exists(stale):
            self.output.warning(
                "removing upstream prebuilt binary shipped in the tarball "
                "(Mach-O arm64): make could otherwise skip relinking and the "
                "package would carry a foreign-ABI executable"
            )
            os.remove(stale)

        optimization_flags = {
            "Debug": "-g -O0",
            "Release": "-O2",
            "RelWithDebInfo": "-g -O2",
            "MinSizeRel": "-Os",
        }.get(str(self.settings.build_type), "-O2")
        # eigen.c redeclares the cexp() builtin and a few loops compare
        # size_t with int; both are upstream warnings, not OHOS issues.
        cflags = f"{optimization_flags} -Wno-incompatible-library-redeclaration"
        compiler = self._compiler()
        # R9: -j1.  CLINKER/CFLAGS are make command line overrides, so the
        # hardcoded "cc" and "-O3" in the upstream Makefile never apply.
        self.run(
            f'make -j1 CLINKER="{compiler}" CFLAGS="{cflags}"',
            cwd=src,
        )

    def package(self):
        src = self._src_dir()
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "seq-gen", src=src, dst=bin_dir, keep_path=False)

        binary = os.path.join(bin_dir, "seq-gen")
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration(
                f"seq-gen executable was not produced by the build: {binary}"
            )

        # The HNP signing tools only exist on the HarmonyOS worker; a freshly
        # linked binary has no .codesign section, so on a host without them
        # this block is a no-op instead of a hard "command not found" error.
        if str(self.settings.os) == "OHOS":
            sign_tool = self._ohos_tool(
                "sign_tool", "/data/service/hnp/bin/binary-sign-tool"
            )
            objcopy = self._ohos_tool(
                "objcopy", "/data/service/hnp/bin/llvm-objcopy"
            )
            if objcopy and os.path.isfile(objcopy):
                self.run(
                    f'"{objcopy}" --remove-section .codesign "{binary}" '
                    "2>/dev/null || true",
                    cwd=self.package_folder,
                )
            if sign_tool and os.path.isfile(sign_tool):
                signed = binary + ".signed"
                self.run(
                    f'"{sign_tool}" sign -inFile "{binary}" '
                    f'-outFile "{signed}" -selfSign 1',
                    cwd=self.package_folder,
                    quiet=True,
                )
                os.replace(signed, binary)
        os.chmod(binary, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
