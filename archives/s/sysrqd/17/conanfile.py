#!/usr/bin/env python3
"""Conan recipe for sysrqd 17 — small daemon to trigger Linux SysRq over the network.

Upstream: https://github.com/jd/sysrqd (GPL-2.0-only, Julien Danjou)
Source archive: Debian `sysrqd_17.orig.tar.gz` (upstream git snapshot 9510edc).
Build system: plain GNU Makefile (single sysrqd.c, no configure, no tests).

OHOS portability notes
----------------------
1. Zero source patches needed. OHOS musl libc exports `crypt`, `daemon`,
   `mlockall`, `setpriority` and `syslog` directly (verified with llvm-nm -D
   on the OHOS sysroot libc.so), and `libcrypt.a` exists in the sysroot, so
   upstream `LDFLAGS += -lcrypt` links as-is.
2. The Makefile derives VERSION via a `grep|head|cut|tr` pipeline; the recipe
   pins `VERSION=17` on the make command line to avoid depending on those
   tools (toybox compatibility) and to keep the build deterministic.
3. `make install` is not used: upstream uses the `install` command which is
   absent on OHOS (knowledge entry E098). package() copies the binary itself
   (to Conan-standard `bin/` so CI L5/L1e gates can see the artifact; upstream
   installs to /usr/sbin).
4. Upstream has NO test suite (no tests/ dir, no test/check make target);
   test_package exercises the installed binary from a consumer perspective.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class SysrqdConan(ConanFile):
    name = "sysrqd"
    version = "17"
    description = (
        "Small daemon to manage Linux Magic SysRq over the network "
        "(TCP port 4094, password authenticated)"
    )
    license = "GPL-2.0-only"
    homepage = "https://github.com/jd/sysrqd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # sysrqd depends only on libc (crypt/daemon/syslog live in OHOS musl libc).
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R33: take the compiler from the Conan conf, never from bare shell vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        # Pin VERSION on the command line: skips the grep|head|cut|tr pipeline
        # in the Makefile and keeps the embedded version deterministic.
        self.run(
            f'make CC="{cc}" VERSION="{self.version}" -j1 sysrqd',
            cwd=self.source_folder,
        )

    def package(self):
        src = self.source_folder
        copy(self, "AUTHORS", src=src, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING*", src=src, dst=os.path.join(self.package_folder, "licenses"))
        # No COPYING file ships with the tarball; the license header of
        # sysrqd.c is the canonical statement, keep ChangeLog/README as doc.
        copy(self, "sysrqd", src=src, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "README.md", src=src, dst=os.path.join(self.package_folder, "share", "sysrqd", "doc"))
        copy(self, "ChangeLog", src=src, dst=os.path.join(self.package_folder, "share", "sysrqd", "doc"))
        # Ensure the exec bit survives packaging.
        os.chmod(os.path.join(self.package_folder, "bin", "sysrqd"), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
