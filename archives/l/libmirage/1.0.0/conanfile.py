#!/usr/bin/env python3
"""Conan recipe for libmirage 1.0.0 on HarmonyOS PC (aarch64, OHOS).

libmirage is the image-interpretation backend of the CDEmu optical drive
suite; cdemud 1.0.0 hard-requires it through pkg-config (libmirage >= 1.0.0).
Per the registry's dependency-first rule (R36/E458, one software per PR),
this recipe is delivered first; cdemud follows in its own PR once
libmirage is published.

Key platform decisions (see notes.md for evidence):
  * Static by default; requesting shared on OHOS is refused when the glib
    dependency has no shared objects (same guard as dbus-glib 0.114 /
    avahi-glib 0.9_rc5). The OHOS glib package is static-only; a shared
    libmirage.so would embed a second private GLib/GObject copy.
  * E236 (stale libtool .la metadata in relocated conan packages): the
    dependency .a files are copied into a build-private, .la-free directory
    and fed to configure through the GLIB_*/GOBJECT_*/GMODULE_*/SNDFILE_*
    cache variables, exactly as validated for dbus-glib 0.114. Generated
    .la files are removed from the final package.
  * 2007-era autotools: config.guess/config.sub OHOS triplet patches,
    configure umask 077 -> 022 (HMDFS self-write rejection) and ACLOCAL/
    AUTOMAKE/AUTOCONF neutralization follow the dbus-glib/libdaemon
    precedents.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibmirageConan(ConanFile):
    name = "libmirage"
    version = "1.0.0"
    description = (
        "libmirage interprets optical media image files (CD/DVD formats) "
        "for the CDEmu suite; backend library of cdemud."
    )
    license = "GPL-2.0-or-later"
    homepage = "https://cdemu.sourceforge.io/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def _require_ohos_shared_glib(self):
        # Upstream glib ships no OHOS shared objects; a shared libmirage
        # would embed a private GLib copy (double GType runtime). Refuse
        # instead of shipping a crashing artifact (dbus-glib 0.114 guard).
        glib_libdir = os.path.join(
            self.dependencies["glib"].package_folder, "lib")
        missing = [name for name in ("libglib-2.0.so", "libgobject-2.0.so")
                   if not os.path.isfile(os.path.join(glib_libdir, name))]
        if missing:
            raise ConanException(
                "glib package lacks required OHOS shared objects: "
                + ", ".join(missing)
                + "; libmirage must be built with shared=False")

    def requirements(self):
        self.requires("glib/2.88.0")
        self.requires("libsndfile/1.2.2")
        # Transitive static link inputs of the glib archives (same as the
        # dbus-glib 0.114 recipe); all published to the registry.
        self.requires("pcre2/10.45")
        self.requires("zlib/1.3.1")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @property
    def _la_free_dir(self):
        return os.path.join(self.build_folder, "dependency-archives")

    def generate(self):
        if self.options.shared and str(self.settings.os) == "OHOS":
            self._require_ohos_shared_glib()

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-gtk-doc")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        tc.generate()

        glib = self.dependencies["glib"].package_folder
        sndfile = self.dependencies["libsndfile"].package_folder
        la = self._la_free_dir

        glib_cflags = (
            f"-I{os.path.join(glib, 'include', 'glib-2.0')} "
            f"-I{os.path.join(glib, 'lib', 'glib-2.0', 'include')}")
        glib_libs = (
            f"-L{la} -Wl,--start-group -lglib-2.0 -lintl -lffi "
            f"-lpcre2-8 -lpcre2-posix -lz -Wl,--end-group")

        # E236: feed configure only through dependency-scoped cache
        # variables pointing at the .la-free directory assembled in build().
        # Appending (not overwriting) preserves the AutotoolsToolchain
        # OHOS compiler/sysroot flags. PKG_CHECK_MODULES honors the
        # pre-set <GROUP>_CFLAGS/<GROUP>_LIBS and skips pkg-config.
        env = Environment()
        env.append("CPPFLAGS",
                   f"-I{os.path.join(glib, 'include')} {glib_cflags} "
                   f"-I{os.path.join(sndfile, 'include')}")
        env.append("LDFLAGS", f"-L{la}")
        env.define("glib_CFLAGS", glib_cflags)
        env.define("glib_LIBS", glib_libs)
        env.define("gobject_CFLAGS", glib_cflags)
        env.define("gobject_LIBS",
                   f"-L{la} -Wl,--start-group -lgobject-2.0 -lglib-2.0 "
                   f"-lintl -lffi -lpcre2-8 -lpcre2-posix -lz -Wl,--end-group")
        env.define("gmodule_CFLAGS", glib_cflags)
        env.define("gmodule_LIBS",
                   f"-L{la} -Wl,--start-group -lgmodule-2.0 -lglib-2.0 "
                   f"-lintl -lffi -lpcre2-8 -lpcre2-posix -lz -Wl,--end-group")
        env.define("sndfile_CFLAGS",
                   f"-I{os.path.join(sndfile, 'include')}")
        env.define("sndfile_LIBS", f"-L{la} -lsndfile -lm")
        # HMDFS timestamp granularity can falsely trigger autotools
        # re-maintenance rules (am--refresh); the shipped Makefile.in is
        # valid, so neutralize regeneration for OHOS builds (dbus-glib /
        # avahi-glib precedent, CI-proven).
        if str(self.settings.os) == "OHOS":
            env.define("ACLOCAL", "true")
            env.define("AUTOMAKE", "true")
            env.define("AUTOCONF", "true")
        env.vars(self, scope="build").save_script("libmirage-deps")

    def build(self):
        apply_conandata_patches(self)

        # E236: copy only the dependency static archives into a
        # build-private directory that contains no .la metadata.
        # Never mutate the conan cache.
        la = self._la_free_dir
        for dep in ("glib", "libsndfile", "pcre2", "zlib"):
            libdir = os.path.join(self.dependencies[dep].package_folder, "lib")
            copy(self, "*.a", src=libdir, dst=la, keep_path=False)
        self.output.info(f"la-free archives: {sorted(os.listdir(la))}")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # E236: remove generated .la metadata from the final package.
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libmirage")
        self.cpp_info.libs = ["mirage"]
        self.cpp_info.includedirs = [
            "include", os.path.join("include", "libmirage-1.0")]
        # Parser/fragment modules build as static archives under
        # lib/libmirage on OHOS (static-only glib); they are payload for
        # runtime module loading and are not link inputs.
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gmodule-2.0",
            "glib::gthread-2.0",
            "glib::gio-2.0",
            "libsndfile::libsndfile",
            "pcre2::pcre2",
            "zlib::zlib",
        ]
