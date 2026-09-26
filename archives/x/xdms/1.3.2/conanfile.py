#!/usr/bin/env python3
"""Conan recipe — xdms 1.3.2 (upstream release, Public Domain).

xDMS unpacks Amiga DMS ("Disk Masher System") archives: it converts `.dms`
disk images back to raw `.adf` images, and can test integrity (`t`), view
archive metadata (`v` / `f`), and show attached FILEID.DIZ (`d`) / Banner (`b`).

Build system: a hand-rolled /bin/sh `configure` (NOT autoconf).  It seds
{CC} {ARCHFLAGS} {ARCHLIBS} {VERSION} {PREFIX} into `Makefile.in` and
`src/Makefile.in`, then a recursive Makefile builds `src/xdms`.  Because it is
not autoconf it rejects any option other than `--prefix=...`, so we invoke it
with `--prefix` only (R1).

OHOS / modern-toolchain adaptation
----------------------------------
The 1.3.2 release does not link on any modern C compiler, glibc/Linux included:

    u_heavy.o: undefined reference to `decode_c'
    u_heavy.o: undefined reference to `decode_p'

`src/cdata.h` defines `INLINE` as plain C99 `inline` for `__GNUC__`.  A C99
`inline` definition is only an *inline definition* — it does not emit an
external definition.  In `u_heavy.c` the helpers `decode_c()` / `decode_p()`
are *called before their definitions*, so the compiler cannot inline them and
emits an external reference that no translation unit provides.  (Upstream dates
from 2006; GCC <5 defaulted to `-std=gnu89`, where plain `inline` emitted the
external definition, so the bug was latent.)

Reproduced on this machine with both `gcc` and `clang` on x86-64 glibc — so it
is a toolchain-generic regression, **not** OHOS-specific.  The minimal fix is to
make `INLINE` a real `static inline`, which restores the intended file-local
semantics.  It is applied via `replace_in_file` in `build()` (no patch file),
matching the pattern used for other recipes in this archive.

Upstream tests
--------------
There are NONE.  The full set of make targets in the 1.3.2 release is:

    Makefile.in      : xdms, clean, install
    src/Makefile.in  : .c.o, xdms, <obj> rules, clean

No `test` / `check` target, and no `tests/`, `test/`, `testing/` or
`regression/` directory exists anywhere in the tarball (36 files total).  The
word "test" in `xdms.txt` refers to the tool's own `t` command, not a test
suite.  Declared honestly as `upstream_total = 0`; functional verification
lives in `test_package/` (see `test_package/MANIFEST.yml`).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get, replace_in_file
from conan.tools.layout import basic_layout


class XdmsConan(ConanFile):
    name = "xdms"
    version = "1.3.2"
    description = "Portable unpacker for Amiga DMS (Disk Masher System) archives"
    license = "Public-Domain"
    homepage = "http://zakalwe.fi/~shd/foss/xdms"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os check must be an explicit allow-list
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xdms supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)
        # xdms builds in-source: configure writes Makefile and src/Makefile next
        # to the sources.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        # R33: take the compiler from Conan conf, never a bare env var
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict)
        return compilers.get("c", "clang") if compilers else "clang"

    def _shell(self):
        # R5: OHOS has no guaranteed /bin/sh for complex scripts; use CONFIG_SHELL
        # (profile [buildenv]) and fall back to bash.
        return (os.environ.get("CONFIG_SHELL") or shutil.which("bash")
                or "/data/service/hnp/bin/bash")

    def _fix_inline(self, src):
        """Turn INLINE into a real `static inline` (see module docstring)."""
        replace_in_file(self, os.path.join(src, "src", "cdata.h"),
                        "#define INLINE inline",
                        "#define INLINE static inline")

    def build(self):
        self._fix_inline(self.source_folder)
        cc = self._cc()
        shell = self._shell()
        # Upstream configure is a sh script that reads CC from the environment and
        # seds it into the Makefiles; --prefix is its only accepted option.
        self.run(f'CC={cc} {shell} ./configure --prefix={self.package_folder}',
                 cwd=self.source_folder)
        self.run(f"make CC={cc} SHELL={shell}", cwd=self.source_folder)

    def package(self):
        src = self.source_folder
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        docdir = os.path.join(self.package_folder, "share", "doc", "xdms-1.3.2")
        for d in (bindir, mandir, docdir):
            os.makedirs(d, exist_ok=True)

        exe_dst = os.path.join(bindir, "xdms")
        shutil.copy2(os.path.join(src, "src", "xdms"), exe_dst)
        os.chmod(exe_dst, 0o755)

        shutil.copy2(os.path.join(src, "xdms.1"), os.path.join(mandir, "xdms.1"))
        for doc in ("xdms.txt", "COPYING", "ChangeLog.txt"):
            p = os.path.join(src, doc)
            if os.path.isfile(p):
                shutil.copy2(p, os.path.join(docdir, doc))

        copy(self, "COPYING", src=src, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # xdms is a CLI tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
