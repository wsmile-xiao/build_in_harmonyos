#!/usr/bin/env python3
"""Conan recipe — libmodbus 3.2.0 (Autotools).

The upstream GitHub tag tarball ships no generated `configure`, and the
remote OHOS CI image has no automake/aclocal (r02 fix for PR #9134).
Instead of bootstrapping with autoreconf at build time, this recipe ships
pre-generated autotools outputs (prebuilt/configure, Makefile.in templates,
aclocal.m4, config.h.in, build-aux auxiliary files) produced locally by
autoreconf from the patched configure.ac. They carry the equivalent fixes
(termios2 combined feature detection, HMDFS umask 007, OHOS-aware
config.guess/config.sub), so the build no longer needs aclocal/automake.

All bootstrap work happens in source(): conan copies sources to the build
folder right after source(), so files created here are what actually gets
configured/built. The generated files are touched newer than configure.ac
so make does not try to re-run aclocal/automake (which the CI image lacks).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibmodbusConan(ConanFile):
    name = "libmodbus"
    version = "3.2.0"
    description = "libmodbus 3.2.0 - A Modbus library for Linux, Mac OS X, FreeBSD, QNX and Win32"
    license = "LGPL-2.1-or-later"
    homepage = "https://libmodbus.org"
    url = "https://github.com/stephane/libmodbus"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        # build-aux/config.guess|config.sub are NEW files (absent from the
        # official tarball) applied as patches below; the pre-generated
        # configure + autotools outputs replace the autoreconf bootstrap.
        copy(self, "patches/0001-build-aux-config.guess.patch",
             src=self.recipe_folder, dst=self.export_sources_folder)
        copy(self, "patches/0002-build-aux-config.sub.patch",
             src=self.recipe_folder, dst=self.export_sources_folder)
        for f in ("configure", "Makefile.in", "aclocal.m4", "config.h.in",
                  "ltmain.sh", "compile", "missing", "install-sh", "depcomp",
                  "test-driver"):
            copy(self, f"prebuilt/{f}",
                 src=self.recipe_folder, dst=self.export_sources_folder)
        copy(self, "prebuilt/src/Makefile.in",
             src=self.recipe_folder, dst=self.export_sources_folder)
        copy(self, "prebuilt/tests/Makefile.in",
             src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # configure.ac patch (termios2 combined detection fix).
        apply_conandata_patches(self)
        # OHOS-aware config.guess/config.sub (new files, absent from tarball).
        self.run("mkdir -p build-aux", cwd=self.source_folder)
        self.run("patch -p1 < patches/0001-build-aux-config.guess.patch",
                 cwd=self.source_folder)
        self.run("patch -p1 < patches/0002-build-aux-config.sub.patch",
                 cwd=self.source_folder)
        # Pre-generated configure + auxiliary files (produced locally from the
        # patched configure.ac via autoreconf; equivalent fixes included).
        self.run("cp -f %s/prebuilt/configure configure && chmod +x configure"
                 % self.export_sources_folder, cwd=self.source_folder)
        for f in ("Makefile.in", "aclocal.m4", "config.h.in",
                  "ltmain.sh", "compile", "missing", "install-sh", "depcomp",
                  "test-driver"):
            build_aux_set = ("ltmain.sh", "compile", "missing", "install-sh",
                             "depcomp", "test-driver")
            self.run("cp -f %s/prebuilt/%s %s"
                     % (self.export_sources_folder, f,
                        "build-aux/%s" % f if f in build_aux_set else f),
                     cwd=self.source_folder)
            if f in build_aux_set:
                self.run("chmod +x build-aux/%s" % f, cwd=self.source_folder)
        self.run("cp -f %s/prebuilt/src/Makefile.in src/" % self.export_sources_folder,
                 cwd=self.source_folder)
        self.run("cp -f %s/prebuilt/tests/Makefile.in tests/" % self.export_sources_folder,
                 cwd=self.source_folder)
        # HMDFS umask trap (E011/E129): mktemp/mkdir under umask 077 creates
        # owner-only dirs owned by the shared account -> not writable by us.
        self.run("sed -i 's/umask 077 && mktemp/umask 007 \\&\\& mktemp/g; "
                 "s/umask 077 && mkdir/umask 007 \\&\\& mkdir/g' "
                 "configure build-aux/config.guess",
                 cwd=self.source_folder)
        # Generated files must be newer than configure.ac/Makefile.am so that
        # make does not attempt to re-run aclocal/automake (absent on CI).
        self.run("touch configure Makefile.in src/Makefile.in tests/Makefile.in "
                 "aclocal.m4 config.h.in build-aux/ltmain.sh build-aux/compile "
                 "build-aux/missing build-aux/install-sh build-aux/depcomp "
                 "build-aux/test-driver build-aux/config.guess build-aux/config.sub",
                 cwd=self.source_folder)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        # Ensure the pre-generated files (configure, Makefile.in templates,
        # config.h.in) are strictly newer than configure.ac/Makefile.am/
        # aclocal.m4 so that make does NOT re-run autoconf/automake to
        # regenerate them (the CI image lacks aclocal, and a regenerated
        # configure would revert the HMDFS umask workaround to umask 077).
        # All autotools SOURCE inputs are forced into the past; only the
        # generated files are bumped to now.
        self.run("touch -d '2000-01-01 00:00:00' configure.ac aclocal.m4 "
                 "Makefile.am m4/libtool.m4 m4/ltoptions.m4 m4/ltsugar.m4 "
                 "m4/ltversion.m4 m4/lt~obsolete.m4",
                 cwd=self.source_folder)
        self.run("touch configure Makefile.in src/Makefile.in tests/Makefile.in "
                 "config.h.in build-aux/ltmain.sh build-aux/compile "
                 "build-aux/missing build-aux/install-sh build-aux/depcomp "
                 "build-aux/test-driver build-aux/config.guess build-aux/config.sub",
                 cwd=self.source_folder)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["modbus"]