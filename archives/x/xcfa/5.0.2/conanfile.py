#!/usr/bin/env python3
"""Conan recipe — xcfa 5.0.2 (Autotools, GTK3 audio conversion suite)

XCFA ("X Convert File Audio") ships a GTK3 GUI (bin/xcfa) and a command
line tool (bin/xcfa_cli) that extract, convert, normalise, split and tag
audio files.  Upstream tarball ships a pre-generated `configure`, so only
the autotools helper is needed (no automake/autoconf bootstrap).

configure.ac hard requirements
  * PKG_CHECK_MODULES : gtk+-3.0, cairo, glib-2.0, gthread-2.0
  * AC_CHECK_LIB      : taglib C bindings (-ltag_c), ALSA (-lasound),
                        libcurl (-lcurl), vte-2.91 (-lvte-2.91)

OHOS / HarmonyOS adaptation (details in notes.md and reports/test-report.md)
  * E007: the 2015-era config.guess/config.sub do not know HarmonyOS
    (`uname -s` = HarmonyOS) -> replaced at build time with self-contained
    OHOS-aware versions; configure's `ac_pwd` probe and `umask 077` are
    adapted for HMDFS (E011, adms/2.3.7 precedent).
  * configure.ac's debug/ansi block *overwrites* CFLAGS, so every
    build-time flag is injected through CPPFLAGS/LDFLAGS/LIBS.
  * The AC_CHECK_LIB probes are not covered by PKG_CHECK_MODULES: their -I
    and -L paths are injected from the Conan packages, together with the
    C++ runtime and zlib needed by taglib's static archive, and glib's
    proxy libintl (gettext() is mapped to g_libintl_gettext() by glib's
    <libintl.h>).
  * patches/ carries the three portability fixes (unavailable cairo-xlib
    headers, vte header lookup, GNU-only get_current_dir_name()).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

# Packages probed by configure.ac through AC_CHECK_LIB (they are not part of
# PKG_CHECK_MODULES, so their include/lib dirs must be injected by hand).
# Full references are used for the lookup (resolved through self.dependencies).
_AC_CHECK_LIB_DEPS = ("libx11/1.8.13", "xorgproto/2025.1", "glib/2.84.0.1",
                      "taglib/1.13.1", "zlib/1.3.1.1", "alsa-lib/1.2.16",
                      "curl/8.15.0", "vte/0.74.2")


class XcfaConan(ConanFile):
    name = "xcfa"
    version = "5.0.2"
    description = "XCFA 5.0.2 — GTK3 audio file conversion suite (xcfa GUI + xcfa_cli)"
    license = "GPL-3.0-or-later"
    homepage = "http://www.xcfa.tuxfamily.org/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: settings.os must be Linux or OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # PKG_CHECK_MODULES hard requirement (gtk+-3.0 pulls cairo/glib/gthread)
        self.requires("gtk/3.24.43")
        # taglib 1.x is the line that builds the official C bindings
        # (libtag_c + tag_c.h); taglib/2.3 has no C wrapper.
        self.requires("taglib/1.13.1")
        self.requires("alsa-lib/1.2.16")
        self.requires("curl/8.15.0")
        self.requires("vte/0.74.2")
        # src/Makefile.am links -lX11 and the poche* sources include
        # <X11/Xlib.h>; xorgproto provides the <X11/X.h> that Xlib.h needs
        # (declared explicitly: reached through libx11 it has no host
        # package folder, so its include dir cannot be resolved).
        self.requires("libx11/1.8.13")
        self.requires("xorgproto/2025.1")
        # zlib: taglib's static archive needs it; glib/libpng pin 1.3.1.1
        # while taglib pins 1.3.1 -> unify on the version the published
        # binaries of gtk's graph were built with.
        self.requires("zlib/1.3.1.1", override=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PKG_CHECK_MODULES needs gtk+-3.0/cairo/glib-2.0/gthread-2.0 from
        # the generated .pc files.
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        includes = []
        for ref in _AC_CHECK_LIB_DEPS:
            dep = self.dependencies[ref]
            info = dep.cpp_info.aggregated_components()
            for inc in info.includedirs:
                includes.append("-I" + os.path.join(dep.package_folder, inc))
            for lib in info.libdirs:
                tc.extra_ldflags.append("-L" + os.path.join(dep.package_folder, lib))

        env = tc.environment()
        # configure.ac replaces CFLAGS with its own debug/ansi value, so any
        # flag added to CFLAGS is lost for the Makefiles -> use CPPFLAGS
        # (prepended to every compile line and left untouched by configure).
        # -fcommon: the 2015 sources use tentative definitions of shared
        # globals; clang 15 defaults to -fno-common -> duplicate symbols.
        env.append("CPPFLAGS", "-fcommon")
        # xcfa's PRINT()/PRINT_FUNC_LF() macros embed __FILE__ (and the
        # compiler records the DWARF comp_dir), which would otherwise ship
        # the build-machine Conan paths inside the binaries (same treatment
        # as libnxml/libmrss/libgcrypt).
        for prefix in (self.source_folder, self.build_folder):
            for flag in ("-ffile-prefix-map", "-fdebug-prefix-map", "-fmacro-prefix-map"):
                env.append("CPPFLAGS", f"{flag}={prefix}=.")
        for inc in includes:
            env.append("CPPFLAGS", inc)
        # LIBS is honoured by configure and ends up last on every link line:
        # -ltag/-lz for taglib's static archive, -lc++ for the C++ runtime,
        # -lintl for glib's proxy libintl implementation.
        env.define("LIBS", "-ltag -lz -lc++ -lintl")
        # configure's compiled sanity checks run on OHOS: the loader must
        # find glib's libintl.so.8 while it probes.
        glib = self.dependencies["glib"]
        glib_libdir = os.path.join(glib.package_folder, glib.cpp_info.libdirs[0])
        env.prepend_path("LD_LIBRARY_PATH", glib_libdir)
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)

        autotools = Autotools(self)

        # E490: restore exec bits HMDFS copies may have dropped.
        for _script in ("configure", "config.guess", "config.sub", "install-sh",
                        "missing", "compile", "depcomp"):
            _path = os.path.join(self.source_folder, _script)
            if os.path.exists(_path):
                os.chmod(_path, 0o755)

        # E007: the shipped config.guess/config.sub predate HarmonyOS.
        self._replace_config_for_ohos()

        # HMDFS getcwd fix (adms/2.3.7 precedent): preset PWD and give
        # configure's ac_pwd probe a $PWD fallback; config.status temp dirs
        # need umask 022 on HMDFS (E011).
        # R6 exception: `configure` is a generated file, but the OHOS-safe
        # config.guess/config.sub and this ac_pwd/umask handling are build-time
        # platform adaptations (no upstream source change, nothing added to
        # patches/) - same treatment as archives/a/aris/2.2.
        os.environ["PWD"] = self.build_folder
        _configure = os.path.join(self.source_folder, "configure")
        with open(_configure) as f:
            _cfg = f.read()
        _cfg = _cfg.replace(
            'ac_pwd=`pwd` && test -n "$ac_pwd" &&',
            'ac_pwd=`pwd` 2>/dev/null || ac_pwd=$PWD\ntest -n "$ac_pwd" &&',
        )
        _cfg = _cfg.replace("umask 077", "umask 022")
        with open(_configure, "w") as f:
            f.write(_cfg)

        autotools.configure()
        autotools.make(args=["-j1"])

    def _replace_config_for_ohos(self):
        """Replace config.guess/config.sub with OHOS-aware versions (E007)."""
        _guess = os.path.join(self.source_folder, "config.guess")
        _sub_path = os.path.join(self.source_folder, "config.sub")
        if not os.path.isfile(_guess) and not os.path.isfile(_sub_path):
            return

        ohos_config_guess = (
            '#!/bin/sh\n'
            '# OHOS-aware config.guess (self-contained)\n'
            'machine=$(uname -m 2>/dev/null || echo unknown)\n'
            'system=$(uname -s 2>/dev/null || echo unknown)\n'
            'case "$system" in\n'
            '    HarmonyOS|OHOS)\n'
            '        echo "${machine}-unknown-linux-ohos"\n'
            '        ;;\n'
            '    *)\n'
            '        echo "${machine}-unknown-linux-gnu"\n'
            '        ;;\n'
            'esac\n'
            'exit 0\n'
        )
        with open(_guess, "w") as f:
            f.write(ohos_config_guess)
        os.chmod(_guess, 0o755)

        ohos_config_sub = (
            '#!/bin/sh\n'
            '# OHOS-aware config.sub (self-contained)\n'
            '# Always pass through the input triplet\n'
            'if [ $# -eq 0 ] || [ -z "$1" ]; then\n'
            '    echo "aarch64-unknown-linux-ohos"\n'
            '    exit 0\n'
            'fi\n'
            'echo "$1"\n'
            'exit 0\n'
        )
        with open(_sub_path, "w") as f:
            f.write(ohos_config_sub)
        os.chmod(_sub_path, 0o755)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
