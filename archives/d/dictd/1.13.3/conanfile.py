#!/usr/bin/env python3
"""Conan recipe - dictd 1.13.3 (DICT protocol server and client tools).

dictd is the RFC 2229 (DICT protocol) server; the source suite also builds
the dict client, the dictzip/dictunzip compressed-dictionary tools and the
dictfmt dictionary-formatting tools.  All artifacts are executables, so the
package is packaged as an application.

Dependency plan (Coordinator-approved option "a"): upstream hard-depends on
libmaa, which has no Conan recipe in this repository.  A minimal static
libmaa is therefore vendored inside this recipe: dictd only consumes
maa_init/maa_shutdown, so a small libmaa.a built from the official libmaa
SourceForge archive (pinned in conandata.yml) is sufficient.  libmaa's own
build system is BSD make (mkc), which is not portable here; the vendored
build compiles its sources directly, supplying the mkc feature macros mkc
would normally detect (SIZEOF_LONG, HAVE_HEADER_SYS_RESOURCE_H) and
pre-generating arggram.c with awk.

The official upstream test entry is `make test` (Makefile.in: test target
runs test/dictd_test and test/dictzip_test); it is executed in build() and
therefore also under the authoritative CI.

On OHOS the tree is built under /data/storage/el2/base (tmpfs) because
HMDFS temp-file/getcwd behaviour is unreliable for long builds; this mirrors
the dialog recipe's proven _build_ohos approach.  Every shell command starts
with an explicit `cd` because the device bash cannot resolve its inherited
working directory at startup (getcwd() fails on HMDFS paths); the leading
`cd` re-establishes a valid internal working directory before the real
command runs.
"""

import hashlib
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class DictdConan(ConanFile):
    name = "dictd"
    version = "1.13.3"
    description = "DICT server (dictd) with dict, dictzip and dictfmt client tools"
    license = "GPL-2.0-or-later"  # parse.c is additionally LGPL-2.0-or-later
    homepage = "https://www.dict.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    _ohos_data_root = "/data/storage/el2/base"

    # libmaa objects compiled into the vendored static library.  The mkc
    # feature-detection macros libmaa's sources expect are provided on the
    # compiler command line: SIZEOF_LONG=8 (aarch64 LP64) and
    # HAVE_HEADER_SYS_RESOURCE_H=1 (musl provides it; timer.c needs struct
    # rusage/getrusage, and maa.c references the tim_* symbols from timer.c,
    # so timer.c must be part of the archive).
    _MAA_CPPFLAGS = (
        "-DMAA_MAJOR=4 -DMAA_MINOR=0 -DMAA_TEENY=0 "
        "-DSIZEOF_LONG=8 -DHAVE_HEADER_SYS_RESOURCE_H=1 -O2"
    )
    _MAA_SRCS = (
        "xmalloc.c hash.c set.c stack.c list.c error.c memory.c "
        "string.c debug.c flags.c maa.c prime.c bit.c timer.c "
        "arg.c pr.c sl.c base64.c base26.c source.c parse-concrete.c "
        "text.c log.c"
    )

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.2")

    def build_requirements(self):
        # dictd's Makefile.in drives every compile/link rule through
        # $(LIBTOOL); the device image ships no libtool binary, so pull one
        # in as a build tool (same approach as the abiword-plugin recipes).
        # tool_requires resolve with the build profile, so CI passes both
        # -pr:h and -pr:b.
        self.tool_requires("libtool/2.5.4")

    def source(self):
        get(self, **self.conan_data["sources"]["dictd"], strip_root=True)
        get(
            self,
            **self.conan_data["sources"]["libmaa"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "vendor", "libmaa"),
        )
        apply_conandata_patches(self)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def build(self):
        if self.settings.os == "OHOS":
            src = self._prepare_ohos_workdir()
        else:
            src = self.source_folder
        libmaa_libdir = self._build_vendored_libmaa(src)
        self._pregenerate_scanners(src)
        self._configure_and_make(src, libmaa_libdir)
        # Official upstream test entry.  Exercises dictfmt/dictunformat/index
        # round-trips, dictzip compression and dictd protocol answers (most
        # server cases run through `dictd --stdin2stdout` pipes; a single
        # group binds localhost:26281).
        self._run_in("CONFIG_SHELL=/bin/sh SHELL=/bin/sh make test", src)
        self._install(src)

    def _run_in(self, command, workdir):
        """Run a command inside workdir (see module docstring for the `cd`)."""
        self.run(
            f"cd '{workdir}' && {command}",
            cwd=workdir,
            env="conanbuild",
        )

    # ── OHOS workdir (tmpfs; HMDFS getcwd/temp files are unreliable) ──

    def _ohos_paths(self):
        build_key = hashlib.sha256(
            os.path.abspath(self.build_folder).encode("utf-8")
        ).hexdigest()[:12]
        root = os.path.join(
            self._ohos_data_root,
            f".conan-build-dictd-{self.version}-{build_key}",
        )
        return root, os.path.join(root, "src")

    def _prepare_ohos_workdir(self):
        root, work = self._ohos_paths()
        expected_prefix = os.path.join(
            self._ohos_data_root,
            f".conan-build-dictd-{self.version}-",
        )
        if not root.startswith(expected_prefix):
            raise ConanException(f"refusing to reset unexpected build root: {root}")
        if os.path.lexists(root):
            if os.path.islink(root):
                os.unlink(root)
            else:
                shutil.rmtree(root)
        os.makedirs(root)
        shutil.copytree(self.source_folder, work, symlinks=True)
        return work

    # ── build steps (src = tree root containing dictd + vendor/libmaa) ──

    def _build_vendored_libmaa(self, src):
        maa_src = os.path.join(src, "vendor", "libmaa", "maa")
        maa_build = os.path.join(src, "maa-build")
        libmaa_a = os.path.join(maa_build, "libmaa.a")
        os.makedirs(maa_build, exist_ok=True)

        cc = os.environ.get("CC", "clang")
        ar = os.environ.get("AR", "ar")
        cppflags = self._MAA_CPPFLAGS

        # arg.c embeds the generated grammar table arggram.c.
        self._run_in("awk -f arggram2c < arggram.txt > arggram.c", maa_src)
        objects = " ".join(
            os.path.join(maa_build, name + ".o") for name in self._MAA_SRCS.split()
        )
        self._run_in(
            f'for f in {self._MAA_SRCS} arggram.c; do '
            f'"{cc}" {cppflags} -I. -c "$f" -o "{maa_build}/$f.o" || exit 1; done',
            maa_src,
        )
        self._run_in(f'"{ar}" rcs "{libmaa_a}" {objects}', maa_build)
        return maa_build

    def _configure_and_make(self, src, libmaa_libdir):
        configure = os.path.join(src, "configure")
        config_shell = os.environ.get("CONFIG_SHELL", "bash")
        cc = os.environ.get("CC", "clang")
        cxx = os.environ.get("CXX", "clang++")
        prefix = self.package_folder.replace("\\", "/")
        zlib_pkg = self.dependencies["zlib"].package_folder
        maa_inc = os.path.join(src, "vendor", "libmaa", "maa")
        cppflags = " ".join([
            f"-I{maa_inc}",
            f"-I{zlib_pkg}/include",
        ])
        ldflags = " ".join([
            f"-L{libmaa_libdir}",
            f"-L{zlib_pkg}/lib",
        ])
        configure_args = f"--prefix={shlex.quote(prefix)}"
        self._run_in(
            f'export PWD="{src}" && '
            f'CC="{cc}" CXX="{cxx}" '
            f'CPPFLAGS="{cppflags}" LDFLAGS="{ldflags}" '
            f'{config_shell} "{configure}" {configure_args}',
            src,
        )
        # The device bash cannot resolve getcwd() at startup, and libtool
        # re-execs itself under $CONFIG_SHELL/$SHELL, so make (and libtool
        # recipe shells) must run under /bin/sh; configure keeps CONFIG_SHELL
        # = bash because that works via the leading `cd` above.
        self._run_in(
            'CONFIG_SHELL=/bin/sh SHELL=/bin/sh make -j1',
            src,
        )

    def _pregenerate_scanners(self, src):
        """Generate the flex/bison outputs ahead of make.

        AC_PROG_LEX(yywrap) demotes LEX to ':' when it cannot find a yywrap
        provider library (-lfl, absent here), which makes the scanner rules
        silently produce nothing.  The dictd scanners implement their own
        yywrap, so generating the four files with the exact upstream rule
        commands up front keeps make from invoking $(LEX)/$(YACC) at all.
        """
        yacc = os.environ.get("YACC", "bison -y")
        bison_flags = "-tdv"
        cmds = (
            "flex servscan.l && mv lex.yy.c servscan.c",
            f"{yacc} {bison_flags} servparse.y; "
            "cmp -s y.tab.h servparse.h || mv y.tab.h servparse.h; "
            "cmp -s y.tab.c servparse.c || mv y.tab.c servparse.c; "
            "rm -f y.tab.h y.tab.c",
            "flex -oclientscan.c clientscan.l",
            f"{yacc} {bison_flags} clientparse.y; "
            "cmp -s y.tab.h clientparse.h || mv y.tab.h clientparse.h; "
            "cmp -s y.tab.c clientparse.c || mv y.tab.c clientparse.c; "
            "rm -f y.tab.h y.tab.c",
        )
        for cmd in cmds:
            self._run_in(cmd, src)

    def _install(self, src):
        """Copy build products into <pkg>/bin.

        The upstream install target drives man-page and script installs and
        is redundant for an application package; the executable set matches
        Makefile.in's EXES plus the configure-generated helper scripts the
        upstream tests rely on (dictl, dictunformat, dictfmt_index2*).
        """
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        executables = (
            "dict",
            "dictd",
            "dictzip",
            "dictfmt",
            "dictl",
            "colorit",
            "dictunformat",
            "dictfmt_index2word",
            "dictfmt_index2suffix",
        )
        for name in executables:
            candidate = os.path.join(src, name)
            if os.path.isfile(candidate):
                shutil.copy2(candidate, os.path.join(bindir, name))
            else:
                self.output.warning(f"dictd: expected executable not found: {name}")
        # dictunzip is not a separate upstream artifact: dictzip.c dispatches on
        # argv[0] (`if (!strcmp(pt, "dictunzip")) ++decompressFlag;`) and the
        # upstream install target never installs a dictunzip file; distributions
        # provide it as a link to dictzip.  Do the same (copy as fallback for
        # filesystems without symlink support).
        dictunzip = os.path.join(bindir, "dictunzip")
        if not os.path.lexists(dictunzip):
            try:
                os.symlink("dictzip", dictunzip)
            except OSError:
                shutil.copy2(os.path.join(bindir, "dictzip"), dictunzip)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
