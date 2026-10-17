#!/usr/bin/env python3
"""Conan recipe — libidl2 0.8.14 (autotools)

libIDL is a small library for creating parse trees of CORBA v2.2 compliant
Interface Definition Language (IDL) files. It is used by ORBit2 and others.

HarmonyOS PC adaptation notes:
  - glib-2.0 (>= 2.4.0) is the only runtime dependency; provided by Conan.
  - Upstream configure/config.sub (2008 vintage) cannot validate the
    aarch64-linux-ohos triplet; 0001-config.sub-ohos.patch adds linux-ohos
    OS family, aarch64 CPU and -linux-ohos suffix recognition. The OHOS
    build passes --build/--host explicitly.
  - flex + bison are required by configure (lexer.l / parser.y); CI has no
    system-level copies, provided via tool_requires.
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
import os


class Libidl2Conan(ConanFile):
    name = "libidl2"
    version = "0.8.14"
    description = "libIDL — library for creating CORBA IDL parse trees"
    license = "LGPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/Archive/libidl"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.in: PKG_CHECK_MODULES(LIBIDL, glib-2.0 >= 2.4.0)
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        # configure.in hard-requires flex (AM_PROG_LEX) and a usable yacc
        # (AC_PROG_YACC) to regenerate lexer.c / parser.c.
        # CI (OHOS build machine) has no system-level flex/bison, so they are
        # provided as tool_requires; a macOS dev box uses the system ones.
        # settings_build selects the toolchain platform; the
        # user.build:flex_bison_native conf lets a local OHOS-settings profile
        # simulate the worker with host tools (see generate()).
        if self.settings_build.os == "OHOS" and not self.conf.get(
                "user.build:flex_bison_native", default=False):
            self.tool_requires("flex/2.6.4")
            self.tool_requires("bison/3.8.2")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(["--enable-static", "--disable-shared"])
        if self.settings.os == "OHOS":
            # 2008-era config.sub/config.guess cannot guess modern triplets;
            # the patched config.sub validates aarch64-linux-ohos
            # (0001-config.sub-ohos.patch), but config.guess still fails on
            # Apple Silicon macOS (aarch64-apple-darwin) and on OHOS.
            # Pin --host (and --build where config.guess cannot guess it).
            tc.configure_args.append("--host=aarch64-linux-ohos")
            if self.settings_build.os == "OHOS":
                if self.conf.get("user.build:flex_bison_native", default=False):
                    # Local simulation on a macOS dev box with an OHOS-settings
                    # profile: report a darwin build machine (a triplet the
                    # bundled config.sub understands) so configure enters
                    # cross mode and skips run-time probes; flex/bison are the
                    # host tools (build_requirements honours the same conf).
                    tc.configure_args.append("--build=x86_64-apple-darwin")
                else:
                    # CI worker: native OHOS build (build == host, configure
                    # may run test programs and the worker can execute them).
                    tc.configure_args.append("--build=aarch64-linux-ohos")
            elif self.settings_build.os == "Macos":
                # macOS dev box, separate build profile: pretend the build
                # machine is x86_64 darwin (a triplet the bundled config.sub
                # understands) so configure enters cross mode and skips
                # run-time probes.
                tc.configure_args.append("--build=x86_64-apple-darwin")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Drop the obsolete libIDL-config-2 shell helper (superseded by the
        # installed libIDL-2.0.pc pkg-config file) and libtool .la files.
        bindir = os.path.join(self.package_folder, "bin")
        for name in ("libIDL-config-2",):
            p = os.path.join(bindir, name)
            if os.path.isfile(p):
                os.unlink(p)
        for root, _dirs, files in os.walk(self.package_folder):
            for f in files:
                if f.endswith(".la"):
                    os.unlink(os.path.join(root, f))

    def package_info(self):
        lib = self.cpp_info.components["libidl2"]
        lib.set_property("pkg_config_name", "libIDL-2.0")
        # Upstream installs headers under $(includedir)/libIDL-2.0/libIDL
        # (include/libIDL/Makefile.am: libIDLincludedir), so consumers keep
        # using #include <libIDL/IDL.h> via this include root.
        lib.includedirs = ["include/libIDL-2.0"]
        lib.libs = ["IDL-2"]
        lib.requires = ["glib::glib-2.0"]
        if self.settings.os in ("Linux", "OHOS"):
            lib.system_libs = ["m", "dl"]
