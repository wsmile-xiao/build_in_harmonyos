#!/usr/bin/env python3
"""Conan recipe — pipebench 0.40 (upstream release) — makefile, single-file C.

pipebench (Thomas Habets) measures stdin/stdout pipe throughput: it copies
stdin to stdout and prints rate statistics. The 0.40 release tarball ships a
trivial Makefile that hardcodes `CC=gcc` and whose `install` target writes to
/usr/local — we therefore build with `make CC=<OHOS clang>` and package the
binary + man page ourselves (never `make install`).

Portability (OHOS/musl):
- upstream omits <stdlib.h>/<string.h> (malloc/strlen/strcpy were implicitly
  declared) — added here.
- it uses legacy BSD types u_int8/16/32/64_t, which glibc provides through
  <sys/types.h> but musl does not; with <stdint.h> we macro-map them to
  uint*_t whenever !__GLIBC__.
- upstream ships no test target (Makefile targets: all/doc/install/clean), so
  there are no upstream tests; the packaged binary is smoke-tested in
  test_package (honest upstream_test = 0, see test_package/MANIFEST.yml).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get, replace_in_file
from conan.tools.layout import basic_layout


class PipebenchConan(ConanFile):
    name = "pipebench"
    version = "0.40"
    description = "Pipe through-put benchmark tool"
    license = "GPL-2.0-or-later"
    homepage = "https://www.habets.pp.se/synscan/programs.html#pipebench"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os check must be an explicit allow-list
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pipebench supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)
        # pipebench is a single-file tool that builds in-source.
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
        return os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"

    def _patch_portability(self, src):
        """Apply the minimal OHOS/musl portability fixes to pipebench.c."""
        cfile = os.path.join(src, "pipebench.c")
        if not os.path.isfile(cfile):
            return
        # missing standard headers (stdlib.h for malloc/free, string.h for strlen/strcpy)
        replace_in_file(self, cfile,
                        "#include <errno.h>",
                        "#include <errno.h>\n#include <stdint.h>\n#include <stdlib.h>\n#include <string.h>")
        # legacy BSD u_int*_t: glibc defines them, musl does not -> map to uint*_t
        replace_in_file(self, cfile,
                        "#ifdef sun\n#define u_int8_t uint8_t\n"
                        "#define u_int16_t uint16_t\n#define u_int32_t uint32_t\n"
                        "#define u_int64_t uint64_t\n#endif",
                        "#if defined(sun) || !defined(__GLIBC__)\n"
                        "#define u_int8_t uint8_t\n#define u_int16_t uint16_t\n"
                        "#define u_int32_t uint32_t\n#define u_int64_t uint64_t\n#endif")

    def build(self):
        self._patch_portability(self.source_folder)
        cc = self._cc()
        shell = self._shell()
        # Upstream Makefile rule: `pipebench: pipebench.c ; $(CC) $(CFLAGS) -o pipebench pipebench.c`
        # CC is hardcoded to gcc upstream, so we override it; CFLAGS come from the
        # Makefile itself (-Wall -w -pedantic).
        self.run(f"make CC={cc} SHELL={shell} pipebench", cwd=self.source_folder)

    def package(self):
        src = self.source_folder
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(mandir, exist_ok=True)
        # upstream `make install` writes to /usr/local, so we package manually
        exe_dst = os.path.join(bindir, "pipebench")
        shutil.copy2(os.path.join(src, "pipebench"), exe_dst)
        os.chmod(exe_dst, 0o755)
        shutil.copy2(os.path.join(src, "pipebench.1"),
                     os.path.join(mandir, "pipebench.1"))
        copy(self, "LICENSE", src=src,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # pipebench is a CLI tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
