#!/usr/bin/env python3
"""Conan recipe for minised 1.16 — a smaller, cheaper, faster SED implementation.

minised is the historic sed by Eric S. Raymond, maintained by ExactCODE. It is
a single-command-line program built from two C translation units (sedcomp.c,
sedexec.c) by a plain Makefile. There is no configure script and no external
dependency beyond libc.

Build system: simple Makefile (no configure, no autotools).
License: BSD-3-Clause (see upstream LICENSE).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get


class MinisedConan(ConanFile):
    name = "minised"
    version = "1.16"
    description = "Smaller, cheaper, faster SED implementation"
    license = "BSD-3-Clause"
    homepage = "https://exactcode.com/opensource/minised/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        # Build in the source tree — the upstream Makefile compiles objects
        # next to the sources and links `minised` in the same directory.
        self.folders.build = "."
        self.folders.generators = "."

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"minised supports Linux and OHOS only (got {self.settings.os})"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_cc(self):
        # Read the C compiler from Conan conf; never hardcode a path (local and
        # CI compiler paths differ). The OHOS profile sets
        # tools.build:compiler_executables={"c": "..."}; fall back to "clang".
        comp_execs = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        return comp_execs.get("c") or "clang"

    def _sdk_llvm_libdir(self):
        # E2160: the OHOS SDK's lld linker is itself linked against
        # libxml2.so.16 (DT_NEEDED, RUNPATH=$ORIGIN/../lib → the SDK llvm/lib
        # ships the ABI-matched 2.14.0). In the CI sandbox lld cannot resolve
        # its own RUNPATH, so the final link step fails with
        # "Error loading shared library libxml2.so.16" / "xmlFreeDoc: symbol
        # not found". Inject lld's native libxml2 (NOT a conan libxml2 — a
        # version/ABI mismatch is exactly what produces the symbol errors).
        # The SDK llvm/lib is derived dynamically from the active compiler's
        # real path: realpath(cc) → .../llvm/bin/clang → .../llvm/lib. No
        # hardcoded SDK version path. minised itself does not depend on
        # libxml2 — only lld does.
        if str(self.settings.os) != "OHOS":
            return ""

        cc = self._get_cc()
        try:
            real_cc = os.path.realpath(cc)
        except OSError:
            return ""
        llvm_lib = os.path.join(
            os.path.dirname(os.path.dirname(real_cc)), "lib"
        )
        if os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
            return llvm_lib
        return ""

    def build(self):
        cc = self._get_cc()
        env = Environment()
        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            self.output.info(
                f"Prepending OHOS SDK linker runtime path: {sdk_llvm_lib}"
            )
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        # Native Makefile: builds sedcomp.o, sedexec.o and links `minised`.
        # The LD_LIBRARY_PATH scope covers the whole make so lld — launched at
        # the final link step — finds its ABI-matched libxml2.so.16. -j1 keeps
        # the (tiny) build deterministic; CFLAGS is appended to by the upstream
        # Makefile (-O1 -Wall -Wwrite-strings) so we only set CC. Non-OHOS:
        # _sdk_llvm_libdir() returns "" → empty env → original logic unchanged.
        with env.vars(self).apply():
            self.run(f'make CC="{cc}" -j1', cwd=self.source_folder)
            # L1: run the upstream test suite. `make check` runs tests/run,
            # which feeds every tests/*.sed program through the freshly built
            # minised and diffs against tests/*.out. It uses mktemp + $(<file)
            # shell features, both available under the OHOS /bin/sh in writable
            # dirs.
            self.run(f'make check CC="{cc}"', cwd=self.source_folder)

    def package(self):
        # OHOS has no `install` coreutil, so do not call `make install`.
        # Copy the freshly built binary, the man page and the license by hand.
        copy(self, "minised", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "minised.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        # CLI tool — no libraries, just the executable.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
