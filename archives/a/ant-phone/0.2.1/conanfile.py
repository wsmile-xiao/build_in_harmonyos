#!/usr/bin/env python3
"""Conan recipe — ant-phone 0.2.1 (Autotools, GTK2 + ALSA + CAPI 2.0).

ANT (Ant is Not a Telephone) — ISDN desktop telephony application.
- Build system: Autotools (configure + make); flex/bison outputs are
  pre-generated in the tarball (calleridlexer.c / calleridparser.c /
  isdnlexer.c / isdnparser.c), so lex/yacc tools are not required.
- Dependencies (both mandatory in configure.ac / src/Makefile.am):
  * gtk+-2.0    via PKG_CHECK_MODULES(DEPS, gtk+-2.0)
  * libsndfile  via AC_CHECK_LIB([sndfile],[sf_open])
  * libasound   via -lasound (ALSA)
  * libcapi20   via -lcapi20 (CAPI 2.0 ISDN)
- Builds a single executable `ant-phone` (bin_PROGRAMS) — package_type
  is application, not library.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.env import Environment
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class AntphoneConan(ConanFile):
    name = "ant-phone"
    version = "0.2.1"
    description = "ANT (Ant is Not a Telephone) — ISDN desktop telephony application (GTK2/ALSA/CAPI 2.0)"
    license = "GPL-2.0-only"
    homepage = "http://www.nongnu.org/ant-phone/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Mandatory per configure.ac:
        #   PKG_CHECK_MODULES(DEPS, gtk+-2.0)  -> gtk2 (pkg_config_name "gtk+-2.0")
        #   AC_CHECK_LIB([sndfile],[sf_open])  -> libsndfile (pkg_config_name "sndfile")
        #   src/Makefile.am LIBS: -lgthread-2.0 -lasound -lcapi20
        self.requires("gtk2/2.24.33", transitive_headers=True, transitive_libs=True)
        self.requires("libsndfile/1.2.2", transitive_headers=True, transitive_libs=True)
        self.requires("alsa-lib/1.2.16.1", transitive_headers=True, transitive_libs=True)
        self.requires("libcapi20/3.27", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # ant-phone ships a 2007-era config.guess/config.sub that cannot
        # recognize aarch64-linux-gnu / aarch64-linux-ohos; autotools-dev
        # provides modern copies. Same pattern as the gtk2 recipe.
        self.tool_requires("autotools-dev/20240727.1-nmu1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsDeps: feed -I/-L/-l from gtk2/libsndfile/alsa-lib/libcapi20
        # into configure/make (configure's AC_CHECK_LIB needs -lsndfile etc).
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        # isdn_lloc/callerid_lloc are tentative definitions shared between
        # lexer.c and parser.c; clang 15 defaults to -fno-common which
        # reports duplicate symbols (clang 3.8+; upstream predates it).
        tc.extra_cflags.append("-fcommon")
        # Cross-compiling cannot run malloc(0) probe, so AC_FUNC_MALLOC
        # defaults ac_cv_func_malloc_0_nonnull=no -> links rpl_malloc with
        # no implementation (undefined symbol). musl's malloc(0) is fine;
        # override the cache var (DRAFT-ohos-autotools-rpl-malloc).
        tc.configure_args.append("ac_cv_func_malloc_0_nonnull=yes")
        tc.configure_args.append("ac_cv_func_realloc_0_nonnull=yes")
        # gtk2 needs its data dir; keep default install prefixes
        tc.configure_args.append("--disable-glibtest")
        # ant-phone bundles gettext's intl/ whose lock.h probes
        # `#pragma weak pthread_cancel` — OHOS libc has no such symbol, so
        # the probe fails to compile. ant-phone is a single-threaded GTK
        # app; libintl's multithread-safety is not required here.
        tc.configure_args.append("--disable-threads")
        if str(self.settings.os) == "OHOS":
            # ant-phone ships a 2007 config.guess that cannot detect OHOS
            # ("cannot guess build type"), same fix as the gtk2 recipe.
            tc.configure_args.extend([
                "--build=aarch64-linux-gnu",
                "--host=aarch64-linux-ohos",
            ])
        # intl/ is bundled (AM_GNU_GETTEXT); keep default.
        tc.generate()
        pc = PkgConfigDeps(self)
        pc.generate()
        # Stage modern config.guess/config.sub over the source tree so the
        # configure --build/--host triplets are validated (2007 scripts
        # reject aarch64-linux-gnu). Same pattern as the gtk2 recipe.
        misc = os.path.join(
            self.dependencies.build["autotools-dev"].package_folder,
            "share", "misc",
        )
        copy(self, "config.guess", src=misc, dst=self.source_folder)
        copy(self, "config.sub", src=misc, dst=self.source_folder)
        # OHOS loader has no default search path for conan-cached shared
        # libs; configure's conftest programs fail unless LD_LIBRARY_PATH
        # points at the dependency lib dirs (same pattern as aaphoto).
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        apply_conandata_patches(self)
        self._patch_configure_tmpdir()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def _patch_configure_tmpdir(self):
        # OHOS distributed fs: `mktemp -d` with umask 077 yields a 0700 dir
        # that the fs refuses extra writes to (EACCES), and chmod is silently
        # ignored. Rewrite configure to drop the temp dir into ${TMPDIR:-.}
        # (a low-traffic dir) with umask 000. Same fix as the gtk2 recipe;
        # the exact patterns shipped by ant-phone 0.2.1 (autoconf 2.61-era)
        # are identical.
        configure = os.path.join(self.source_folder, "configure")
        with open(configure, encoding="utf-8", errors="replace") as h:
            content = h.read()
        replaced = [
            ('tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
             'tmp=`(umask 000 && mktemp -d "${TMPDIR:-.}/confXXXXXX") 2>/dev/null` && { chmod 777 "$tmp" 2>/dev/null || true; } &&'),
            ("tmp=./conf$$-$RANDOM",
             "tmp=${TMPDIR:-.}/conf$$-$RANDOM"),
        ]
        optional = [
            ("(umask 077 && mkdir \"$tmp\")",
             "(umask 000 && mkdir \"$tmp\")"),
        ]
        changed = False
        for old, new in replaced:
            if new in content:
                continue
            if old not in content:
                self.output.warning(f"configure tmpdir pattern not found: {old[:50]}")
                continue
            content = content.replace(old, new, 1)
            changed = True
        for old, new in optional:
            if old in content and new not in content:
                content = content.replace(old, new, 1)
                changed = True
        if changed:
            with open(configure, "w", encoding="utf-8", newline="\n") as h:
                h.write(content)
            self.output.info("patched configure tmpdir to ${TMPDIR:-.} umask-000")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Application: only the bin/ path matters; libs are runtime deps.
        self.cpp_info.bindirs = ["bin"]
