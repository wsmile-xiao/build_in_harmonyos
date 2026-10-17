#!/usr/bin/env python3
"""Conan recipe — webbench 1.5 (upstream release, GPL-2.0-or-later).

WebBench (Radim Kolar, 1997-2004) is a simple forking HTTP/proxy server
benchmark: it forks N client processes, hammers a URL for T seconds, and
reports pages/min and bytes/sec.  It exercises fork(2), socket(2)/connect(2),
alarm(2)/sigaction(2), pipe(2), fdopen(3) and gethostbyname(3) — a useful POSIX
surface check on a new platform.

Build system: a plain GNU/BSD Makefile (`make webbench`).  The `all` target also
runs `ctags`, which is not needed, so the explicit `webbench` target is built.

OHOS / modern-toolchain adaptation
----------------------------------
The 1.5 release does not compile on any modern system, Linux included:

    webbench.c:21:10: fatal error: rpc/types.h: No such file or directory

`webbench.c` includes `<rpc/types.h>` — the Sun RPC header.  glibc **removed
Sun RPC from libc in 2.26 (2017)**; it now lives in libtirpc and the header is
only present when `libtirpc-dev` is installed.  musl (and therefore OHOS) has
never shipped it.  So the include is dead on both glibc>=2.26 and OHOS.

Nothing from that header is used: `MAXHOSTNAMELEN` comes from `<sys/param.h>`
(verified = 64 on the OHOS target), `bzero`/`index` from `<strings.h>`
(verified present on OHOS), `getopt_long` from `<getopt.h>`, and the socket
surface from `socket.c`.  Removing the vestigial include is therefore both
necessary and sufficient — verified by building and running the benchmark.

The 1.5 release also does not *run* correctly on OHOS/musl.  `bench()` in the
parent unbuffers the pipe it reads child results from:

    f=fdopen(mypipe[0],"r");
    setvbuf(f,NULL,_IONBF,0);          /* webbench.c */

On OHOS that call leaves the stream unable to parse: the following
`fscanf(f,"%d %d %d",&i,&j,&k)` returns -1 with `feof`/`ferror` clear and
`errno` 0, so the parent takes the `pid<2` branch and prints "Some of our
childrens died." every run, reporting `Speed=0 ... Requests: 0 susceed`.
Characterised on the OHOS target with a minimal reproducer: identical code
without the `setvbuf` call parses the same pipe correctly (`fscanf` -> 3);
`fgets`+`sscanf`, `fread` and raw `read` all work; only the
`setvbuf(_IONBF)` + `fscanf` combination fails.  glibc is unaffected (the same
source benchmarks correctly on Linux x86-64).

Fix: drop the unbuffering call.  The parent reads a fixed number of integer
triples (the loop runs exactly `clients` times), so the stream's buffering mode
cannot change the parsed values — the two platforms then agree.  Buffering the
read side is safe here because a pipe `read()` returns as soon as data is
available rather than waiting to fill the buffer.

Upstream tests
--------------
There are NONE.  The Makefile's complete target list is:

    all, tags, install, webbench, webbench.o, clean, tar
    .PHONY: clean install all tar

There is no `test` or `check` target and the tarball contains no `tests/`,
`test/` or `regression/` directory (9 entries total including `debian/`).
Declared honestly as `upstream_total = 0`; functional verification lives in
`test_package/` (see `test_package/MANIFEST.yml`).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get, replace_in_file
from conan.tools.layout import basic_layout


class WebbenchConan(ConanFile):
    name = "webbench"
    version = "1.5"
    description = "Simple forking HTTP/proxy server benchmark tool"
    license = "GPL-2.0-or-later"
    homepage = "http://home.tiscali.cz/~cz210552/webbench.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os check must be an explicit allow-list
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"webbench supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)
        # webbench builds in-source (Makefile next to the sources)
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

    def _drop_rpc_types(self, src):
        """Remove the vestigial Sun RPC include (see module docstring)."""
        cfile = os.path.join(src, "webbench.c")
        if not os.path.isfile(cfile):
            return
        replace_in_file(self, cfile, "#include <rpc/types.h>\n", "")

    def _drop_ionbf_setvbuf(self, src):
        """Drop the unbuffering of the parent's result pipe (see module docstring).

        On OHOS/musl, `setvbuf(stream, NULL, _IONBF, 0)` on a *read* stream makes
        the following `fscanf` return -1 without setting feof/ferror/errno, which
        makes webbench report "Some of our childrens died." and 0 requests.
        """
        cfile = os.path.join(src, "webbench.c")
        if not os.path.isfile(cfile):
            return
        replace_in_file(self, cfile, "  setvbuf(f,NULL,_IONBF,0);\n", "")

    def build(self):
        self._drop_rpc_types(self.source_folder)
        self._drop_ionbf_setvbuf(self.source_folder)
        cc = self._cc()
        shell = self._shell()
        # Upstream Makefile: `webbench: webbench.o Makefile` with CC?=gcc, CFLAGS?=
        # The `all` target also invokes ctags, so build the explicit target.
        self.run(f"make webbench CC={cc} SHELL={shell}", cwd=self.source_folder)

    def package(self):
        src = self.source_folder
        bindir = os.path.join(self.package_folder, "bin")
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        docdir = os.path.join(self.package_folder, "share", "doc", "webbench")
        for d in (bindir, mandir, docdir):
            os.makedirs(d, exist_ok=True)

        exe_dst = os.path.join(bindir, "webbench")
        shutil.copy2(os.path.join(src, "webbench"), exe_dst)
        os.chmod(exe_dst, 0o755)

        shutil.copy2(os.path.join(src, "webbench.1"), os.path.join(mandir, "webbench.1"))
        # upstream ships COPYRIGHT/ChangeLog as symlinks into debian/
        for srcname, dstname in (("debian/copyright", "COPYRIGHT"),
                                 ("debian/changelog", "ChangeLog")):
            p = os.path.join(src, srcname)
            if os.path.isfile(p):
                shutil.copy2(p, os.path.join(docdir, dstname))

        p = os.path.join(src, "debian", "copyright")
        if os.path.isfile(p):
            copy(self, "copyright", src=os.path.join(src, "debian"),
                 dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # webbench is a CLI tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
