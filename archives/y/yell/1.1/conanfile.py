#!/usr/bin/env python3
"""Conan recipe — yell 1.1 (command-line PC speaker bell).

yell 1.1 (2002, ehaupt / critical.ch; FreeBSD port audio/yell) is a tiny C
CLI that plays a short tune on the PC speaker by writing an ASCII tune
string to /dev/speaker.  The upstream tarball ships exactly four files
(`Makefile`, `yell.c`, `yell.h`, `README`) with **no external library
dependencies** — the only system requirement is libc.

The upstream `Makefile` is a FreeBSD port leftover and is deliberately NOT
used: its `install` target hardcodes `BINDIR=/usr/local/bin`, `chown root`
and `chmod 4110` (setuid), none of which apply to a Conan package or to the
OHOS sandbox.  This recipe reproduces the port's `do-build` one-liner
(`${CC} ${WRKSRC}/yell.c ${CFLAGS} -o ${WRKSRC}/${PORTNAME}`) with the OHOS
overrides below, and packages the built binary directly.

OHOS adaptation notes:

* The upstream source includes `<dev/speaker/speaker.h>`, a FreeBSD kernel
  header that does not exist on OHOS (and whose declarations the code never
  uses — the only syscalls are `open`/`write`/`close`, declared by
  `<fcntl.h>`/`<unistd.h>`).  Portability patch 0001 replaces that include
  with `<unistd.h>` (which also declares `write`/`close` — on FreeBSD they
  leaked in transitively through the speaker header, so dropping it without
  a replacement breaks the build with implicit-declaration errors).
* The FreeBSD port's `ONLY_FOR_ARCHS= i386 amd64` comes from the kernel
  `speaker(4)` device, not from the C source; the code itself is portable
  C89 and compiles cleanly for aarch64.
* The compiler's stdout/stderr are redirected into a log file inside the
  build folder (and echoed afterwards).  With this platform's
  `/system/bin/sh` as the recipe shell, a compiler whose stdio is wired
  directly into the CI harness' capture pipe exits 1 **without any
  diagnostics**, while the identical command succeeds when its stdio is a
  regular file (same measured behaviour as zpaq 7.15).
* No `-static-libstdc++` needed: the binary is pure C, so its only
  `DT_NEEDED` entry is `libc.so` (verified with readelf).

Runtime behaviour on OHOS: there is no PC speaker (`/dev/speaker` does not
exist), so `play()`'s `open()` fails, nothing is written and `main()` still
returns `EXIT_SUCCESS`.  The test_package asserts exactly this graceful
degradation contract.

The package ships `bin/yell`, the upstream `README` under `licenses/` and a
`LICENSE` attribution note (the tarball carries no licence file; the FreeBSD
port records `LICENSE= BSD2CLAUSE`).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class YellConan(ConanFile):
    name = "yell"
    version = "1.1"
    description = (
        "yell 1.1 — command-line PC speaker bell (plays a short tune on "
        "/dev/speaker; useful as a shell notification, e.g. make buildworld && yell)"
    )
    license = "BSD-2-Clause"
    homepage = "https://www.critical.ch/yell/"
    url = "https://www.critical.ch/yell/"

    package_type = "application"
    topics = ("yell", "speaker", "beep", "bell", "notification", "audio")

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: platform gate must accept both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "yell is supported only on Linux/OHOS, not "
                + str(self.settings.os)
            )

    def export_sources(self):
        export_conandata_patches(self)
        # The LICENSE attribution file lives next to the recipe (the upstream
        # tarball ships no licence file, so it cannot come from conandata).
        # Export it so it survives `conan create`'s recipe cache copy and can
        # be packaged from the source folder (during `conan create`,
        # self.recipe_folder points at the cache copy, where un-exported
        # recipe-side files do not exist).
        copy(
            self,
            "LICENSE",
            src=os.path.join(self.recipe_folder),
            dst=self.export_sources_folder,
        )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Portability patch 0001: <dev/speaker/speaker.h> (FreeBSD kernel
        # header, declarations unused) -> <unistd.h>.  See module docstring.
        apply_conandata_patches(self)

        # R33: the C compiler comes from the Conan conf
        # (tools.build:compiler_executables), never from bare shell vars.
        comp = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = comp.get("cc") or "clang"

        # Equivalent of the FreeBSD port's do-build one-liner
        # (`${CC} ${WRKSRC}/yell.c ${CFLAGS} -o ${WRKSRC}/${PORTNAME}`),
        # single translation unit, no external libraries.
        #
        # Compiler stdio is redirected into a log file: /system/bin/sh as the
        # recipe shell silently kills compilers wired into the CI capture
        # pipe (exit 1, no diagnostics); see module docstring.
        build_log = os.path.join(self.build_folder, "yell-build.log")
        self.run(
            f'{cc} -O3 -DNDEBUG -Wall yell.c -o yell > "{build_log}" 2>&1; '
            f'rc=$?; cat "{build_log}"; exit $rc',
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        # The only built artifact is the CLI.  The upstream Makefile's
        # install target (BINDIR=/usr/local/bin + chown root + setuid 4110)
        # is intentionally not used.
        copy(
            self,
            "yell",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        # Licence attribution: the upstream tarball ships no licence file;
        # the FreeBSD port records LICENSE= BSD2CLAUSE.  Ship the upstream
        # README plus an explanatory LICENSE note.
        copy(
            self,
            "README",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # Command-line tool, not a library (no cpp_info.libs)
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
