#!/usr/bin/env python3
"""Conan recipe - recode 3.7.15 (Autotools)."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, export_conandata_patches, get, replace_in_file, save
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RecodeConan(ConanFile):
    name = "recode"
    version = "3.7.15"
    description = "Conversion between character sets and surfaces"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/rrthomas/recode"
    url = "https://github.com/rrthomas/recode"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    win_bash = True
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # HarmonyOS libc's iconv implementation does not support the full
        # charset set needed by recode's upstream iconv tests.
        self.requires("libiconv/1.17")

    def build_requirements(self):
        # Minimal OpenHarmony build images provide autoconf and m4, but not
        # the Automake/Libtool tools needed to bootstrap this source tree.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("gettext/0.22.5.1")
        self.tool_requires("m4/1.4.19")

    def layout(self):
        basic_layout(self)
        # Recode's generated sources are written into the source tree by its
        # Automake rules, so an out-of-source build breaks their relative paths.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(
            self,
            **self.conan_data["gnulib"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "gnulib"),
        )

    def generate(self):
        iconv = self.dependencies["libiconv"]
        iconv_prefix = iconv.package_folder
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-gcc-warnings",
            "--disable-nls",
            f"--with-libiconv-prefix={iconv_prefix}",
        ])
        tc.extra_cflags.extend(
            f"-I{os.path.join(iconv_prefix, include_dir)}"
            for include_dir in iconv.cpp_info.includedirs
        )
        tc.extra_ldflags.extend(
            f"-L{os.path.join(iconv_prefix, lib_dir)}"
            for lib_dir in iconv.cpp_info.libdirs
        )
        AutotoolsDeps(self).generate()
        tc.generate()

    def build(self):
        # The tagged Git tree intentionally omits generated Autotools files.
        # The matching gnulib snapshot above makes bootstrap reproducible.
        build_tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(build_tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = build_tmpdir
        iconv_program = os.path.join(
            self.dependencies["libiconv"].package_folder,
            "bin",
            "iconv",
        )
        if not os.path.isfile(iconv_program):
            raise ConanException(
                f"libiconv iconv tool not found: {iconv_program}"
            )
        gettext_aclocal = os.path.join(
            self.dependencies.build["gettext"].package_folder,
            "share",
            "aclocal",
        )
        if os.path.isdir(gettext_aclocal):
            existing_aclocal = os.environ.get("ACLOCAL_PATH", "")
            os.environ["ACLOCAL_PATH"] = os.pathsep.join(
                path for path in (gettext_aclocal, existing_aclocal) if path
            )
        gettext_about_nls = os.path.join(
            self.dependencies.build["gettext"].package_folder,
            "share",
            "gettext",
            "ABOUT-NLS",
        )
        if os.path.isfile(gettext_about_nls):
            copy(
                self,
                "ABOUT-NLS",
                src=os.path.dirname(gettext_about_nls),
                dst=self.source_folder,
            )
        gettext_makevars = os.path.join(
            self.dependencies.build["gettext"].package_folder,
            "share",
            "gettext",
            "po",
            "Makevars.template",
        )
        if os.path.isfile(gettext_makevars):
            copy(
                self,
                "Makevars.template",
                src=os.path.dirname(gettext_makevars),
                dst=os.path.join(self.source_folder, "po"),
            )
        bootstrap_conf = os.path.join(self.source_folder, "bootstrap.conf")
        if os.path.isfile(bootstrap_conf):
            # These release-only tools are not needed for the library/CLI
            # build and are absent from minimal OpenHarmony build images.
            for prerequisite in (
                "        gpg        1.4.11  https://www.gnupg.org\n",
                "        help2man   1.29    https://www.gnu.org/s/help2man\n",
                "        makeinfo   5.2     https://www.gnu.org/s/texinfo\n",
            ):
                replace_in_file(self, bootstrap_conf, prerequisite, "")
        configure_ac = os.path.join(self.source_folder, "configure.ac")
        if os.path.isfile(configure_ac):
            # --disable-nls with --skip-po must not leave an unconditional
            # po/Makefile.in target in the generated configure script.
            replace_in_file(
                self,
                configure_ac,
                "          po/Makefile.in src/Makefile src/recode.x\n",
                "          src/Makefile src/recode.x\n",
            )
        makefile_am = os.path.join(self.source_folder, "Makefile.am")
        if os.path.isfile(makefile_am):
            replace_in_file(
                self,
                makefile_am,
                "SUBDIRS = doc lib src po tests contrib\n",
                "SUBDIRS = doc lib src tests contrib\n",
            )
        tables_py = os.path.join(self.source_folder, "tables.py")
        if os.path.isfile(tables_py):
            # HarmonyOS Python cannot consume os.popen() output because its
            # pipe reader returns text where the CPython buffer expects bytes.
            # Keep the generator's text parsing, but bridge iconv through a
            # regular file under TMPDIR instead of a Python pipe.
            replace_in_file(
                self,
                tables_py,
                "        import os\n"
                "        names = []\n"
                "        for line in os.popen('iconv -l'):\n",
                "        import os\n"
                "        import subprocess\n"
                "        import tempfile\n"
                "        names = []\n"
                "        iconv_program = " + repr(iconv_program) + "\n"
                "        iconv_fd, iconv_list = tempfile.mkstemp(prefix='recode-iconv-')\n"
                "        try:\n"
                "            with os.fdopen(iconv_fd, 'w+') as iconv_output:\n"
                "                subprocess.run([iconv_program, '-l'], stdout=iconv_output, check=True)\n"
                "                iconv_output.seek(0)\n"
                "                iconv_lines = iconv_output.readlines()\n"
                "        finally:\n"
                "            try:\n"
                "                os.unlink(iconv_list)\n"
                "            except OSError:\n"
                "                pass\n"
                "        for line in iconv_lines:\n",
            )
        autopoint_wrapper = os.path.join(self.build_folder, "autopoint-wrapper")
        save(
            self,
            autopoint_wrapper,
            "#!/bin/sh\n"
            "case \"$1\" in\n"
            "  --version) echo 'autopoint (GNU gettext) 0.26' ;;\n"
            "esac\n"
            "exit 0\n",
        )
        gnulib_tool = os.path.join(self.source_folder, "gnulib", "gnulib-tool")
        replace_in_file(
            self,
            gnulib_tool,
            '(umask 077 && mktemp -d "$TMPDIR/glXXXXXX")',
            "(umask 022 && tmp=$TMPDIR/gl$$-$RANDOM && "
            'mkdir "$tmp" && printf \'%s\\n\' "$tmp")',
        )
        bootstrap = os.path.join(self.source_folder, "bootstrap")
        replace_in_file(
            self,
            bootstrap,
            "gnulib_path=\n",
            "gnulib_path="
            f"{shlex.quote(os.path.join(self.source_folder, 'gnulib'))}\n",
        )
        replace_in_file(
            self,
            bootstrap,
            'test -n "$gnulib_path" || gnulib_path=gnulib',
            "test -n \"$gnulib_path\" || gnulib_path="
            f"{shlex.quote(os.path.join(self.source_folder, 'gnulib'))}",
        )
        self.run(
            f"chmod +x {shlex.quote(autopoint_wrapper)}",
            cwd=self.build_folder,
            env="conanbuild",
        )
        self.run(
            f"TMPDIR={shlex.quote(build_tmpdir)} "
            "PERL=/data/service/hnp/bin/perl "
            "LEX=/data/service/hnp/bin/flex "
            "M4=/data/service/hnp/bin/m4 "
            "AUTOCONF=/data/service/hnp/bin/autoconf "
            "AUTORECONF=/data/service/hnp/bin/autoreconf "
            "AUTOHEADER=/data/service/hnp/bin/autoheader "
            "AUTOM4TE=/data/service/hnp/bin/autom4te "
            f"AUTOPOINT={shlex.quote(autopoint_wrapper)} "
            "./bootstrap --skip-po --copy",
            cwd=self.source_folder,
            env="conanbuild",
        )
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            replace_in_file(self, configure, "umask 077", "umask 022")
            # Autoconf's pwd subprocess can lose the HMDFS cwd after gnulib
            # bootstrap; use the shell-maintained path for this check.
            replace_in_file(
                self,
                configure,
                "ac_pwd=`pwd` && test -n \"$ac_pwd\" &&",
                "ac_pwd=${PWD-} && test -n \"$ac_pwd\" &&",
            )
        config_guess = os.path.join(self.source_folder, "build-aux", "config.guess")
        if os.path.isfile(config_guess):
            # GNU config.guess uses a GUESS variable and prints it after the
            # main system case.  Keep the branch in that case so HarmonyOS
            # never falls through to the compiler-based probe.
            replace_in_file(
                self,
                config_guess,
                "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n"
                "    *:NetBSD:*:*)",
                "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n"
                "    *:HarmonyOS:*:*)\n"
                "\tcase \"$UNAME_MACHINE\" in\n"
                "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                "\t    i?86)         MACHINE=i686 ;;\n"
                "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
                "\tesac\n"
                "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                "\t;;\n\n"
                "    *:NetBSD:*:*)",
            )
        config_sub = os.path.join(self.source_folder, "build-aux", "config.sub")
        if os.path.isfile(config_sub):
            replace_in_file(self, config_sub, "| fiwix* | mlibc* )", "| fiwix* | mlibc* | ohos* )")
            replace_in_file(self, config_sub, "| linux-mlibc* )", "| linux-mlibc* | linux-ohos* )")
        if os.path.isfile(config_guess):
            replace_in_file(self, config_guess, "umask 077", "umask 022")
        # Conan may retain an invalid HMDFS cwd after gnulib's child shells;
        # provide configure with the canonical path through the environment.
        os.environ["PWD"] = self.build_folder
        os.environ["MAKE"] = "/data/service/hnp/bin/make"
        autotools = Autotools(self)
        autotools.configure()
        # Build gnulib first because src/recode depends on generated headers
        # and libgnu.la from the lib subdirectory.  The generated strip tables
        # are source files of src, so keep both stages serial.
        autotools.make(args=["-C", "lib", "all", "-j1"])
        autotools.make(args=["-C", "src", "recode", "-j1"])

    def package(self):
        # help2man cannot execute the target binary during cross packaging.
        Autotools(self).install(target="install-exec")
        copy(
            self,
            pattern="*.h",
            src=os.path.join(self.source_folder, "src"),
            dst=os.path.join(self.package_folder, "include"),
        )

    def package_info(self):
        self.cpp_info.libs = ["recode"]
        self.cpp_info.bindirs = ["bin"]
