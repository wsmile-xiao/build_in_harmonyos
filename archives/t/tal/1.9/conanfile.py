#!/usr/bin/env python3
"""Conan recipe for tal 1.9 - trailer alignment filter.

tal reads lines of text, finds the trailing characters they have in common
(a "trailer", e.g. ``*/`` or a macro-continuation backslash) and aligns them
in one column.  Upstream ships a single ``tal.c`` plus a hand-written Makefile.

OHOS notes
----------
* The upstream platform targets (``make linux``/``sunos5``/...) hard-code
  ``CC=gcc`` and ``-ansi``.  ``-ansi`` defines ``__STRICT_ANSI__``, so musl
  hides the POSIX declarations of ``strdup()``/``strcasecmp()``; C89 then
  declares them implicitly as returning ``int`` and the explicit ``(char *)``
  casts truncate every 64-bit heap pointer.  The build succeeds with only
  ``-Wint-to-pointer-cast`` warnings, but the binary dies with SIGSEGV on the
  first input line.  The recipe builds the generic ``tal`` target with
  clang's default C dialect and turns implicit function declarations into
  errors, so this regression cannot come back silently.
* Plain ``make`` without an ``OS`` environment variable falls through to the
  ``_tal`` target, which only prints a hint and exits 0 without building
  anything - hence the explicit ``tal`` target.
* ``-static-pie`` keeps PIE/RELRO/BIND_NOW while making the delivered binary
  self-contained, so test_package executes the very same artifact natively
  on AArch64 and through qemu-aarch64 on x86 runners (a dynamically linked
  OHOS executable cannot start there: no /lib/ld-musl-aarch64.so.1).
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class TalConan(ConanFile):
    name = "tal"
    version = "1.9"
    description = "Filter that aligns common trailing characters at the ends of text lines"
    license = "LicenseRef-tal"
    homepage = "https://thomasjensen.com/software/tal/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("text", "filter", "alignment", "vim")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tal is validated on Linux/OHOS only, not {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        # Upstream compiles and links in one "$(CC) $(CFLAGS)" step, so the link
        # mode travels in CFLAGS; command-line variables override the Makefile.
        cflags = "-O2 -Werror=implicit-function-declaration -static-pie"
        self.run(shlex.join(["make", "-j1", "tal", f"CC={cc}", f"CFLAGS={cflags}"]),
                 cwd=self.source_folder, env="conanbuild")

    def package(self):
        copy(self, "tal", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "tal.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
