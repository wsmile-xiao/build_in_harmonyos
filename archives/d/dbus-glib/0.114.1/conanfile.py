#!/usr/bin/env python3
"""Conan recipe for dbus-glib 0.114 on HarmonyOS PC (aarch64, OHOS).

Key platform decisions (see notes.md for evidence):
  * Static by default and shared builds are refused when the glib
    dependency has no shared objects (same guard as avahi-glib 0.9_rc5).
    The OHOS glib package is static-only; linking it into a shared
    libdbus-glib would embed a second private copy of GLib/GObject and
    crash consumers with a double GType runtime (observed: PC=0 SIGSEGV
    in the last g_object_unref of /specialized-types/ao/GSList).
  * E236 (stale libtool .la metadata in relocated conan packages): the
    dependency .a files are copied into a build-private, .la-free
    directory and fed to configure through the GLIB_*/DBUS_* cache
    variables, exactly as validated on device. Generated .la files are
    removed from the final package.
  * dbus only ships dbus.pc, but configure checks the dbus-1 module and
    probes expat through AC_CHECK_LIB (not pkg-config), so both are
    handled through explicit CFLAGS/LIBS instead of PKG_CONFIG_PATH.
  * 0.114.1 (this revision) exists so that a single graph can carry both
    the GTK3 stack and dbus-glib: gtk/3.24.4x pins glib/2.84.0.1, so the
    pins below follow the GTK3 stack (glib/2.84.0.1, expat/2.8.2.1,
    zlib/1.3.1.1). glib/2.84.0.1 ships shared objects only, so the
    la-free static archive directory cannot satisfy the -l names: the
    in-tree dbus-gmain check programs reuse GLIB_LIBS and failed to link
    ("unable to find library -lgio-2.0") until GLIB_LIBS also pointed at
    glib's shared libdir.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm, rmdir
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DbusGlibConan(ConanFile):
    name = "dbus-glib"
    version = "0.114.1"
    description = (
        "dbus-glib provides GLib/GObject bindings for the D-Bus message system "
        "(legacy high-level API above libdbus)."
    )
    license = ("MIT", "AFL-2.1")
    homepage = "https://dbus.freedesktop.org/doc/dbus-glib/"
    url = "https://gitlab.freedesktop.org/dbus/dbus-glib"

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
        # Upstream glib ships no OHOS shared objects; a shared
        # libdbus-glib would embed a private GLib copy (double GType
        # runtime, observed PC=0 SIGSEGV). Refuse instead of shipping a
        # crashing artifact (same guard style as avahi-glib 0.9_rc5).
        glib_libdir = os.path.join(
            self.dependencies["glib"].package_folder, "lib")
        missing = [name for name in ("libglib-2.0.so", "libgobject-2.0.so")
                   if not os.path.isfile(os.path.join(glib_libdir, name))]
        if missing:
            raise ConanException(
                "glib package lacks required OHOS shared objects: "
                + ", ".join(missing)
                + "; dbus-glib must be built with shared=False")

    def requirements(self):
        # Aligned with the GTK3 stack (gtk/3.24.4x): one graph must be
        # able to carry both gtk3 and dbus-glib. dbus/1.14.10 pins
        # expat/2.8.2 while the GTK3 chain pins expat/2.8.2.1, so the
        # alignment is declared here as an override: a consumer-side
        # override would additionally change this recipe's package_id and
        # leave CI (which only builds the package under test) without a
        # binary to install.
        self.requires("glib/2.84.0.1")
        self.requires("dbus/1.14.10")
        # Direct link inputs of the static archives below; all published.
        # expat needs an override because dbus/1.14.10 still pins 2.8.2.
        # zlib is not declared: glib/2.84.0.1 is shared-only, so zlib is
        # no longer a link input, and an override-only requirement is
        # marked "Skip" and exposes no package folder.
        self.requires("expat/2.8.2.1", override=True)
        self.requires("pcre2/10.45")

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
        dbus = self.dependencies["dbus"].package_folder
        expat = self.dependencies["expat"].package_folder
        la = self._la_free_dir

        # E236: feed configure only through dependency-scoped cache
        # variables pointing at the .la-free directory assembled in build().
        # Append (not overwrite) the toolchain flag vars so OHOS compiler
        # and sysroot flags injected by AutotoolsToolchain are preserved.
        env = Environment()
        env.append("CPPFLAGS",
                   f"-I{os.path.join(expat, 'include')} "
                   f"-I{os.path.join(glib, 'include')} "
                   f"-I{os.path.join(glib, 'include', 'glib-2.0')} "
                   f"-I{os.path.join(glib, 'lib', 'glib-2.0', 'include')} "
                   f"-I{os.path.join(dbus, 'include')} "
                   f"-I{os.path.join(dbus, 'include', 'dbus-1.0')}")
        # -Wl,-rpath over the la-free dir lets freshly built in-tree
        # tools (dbus-binding-tool, run during `make` for the examples)
        # resolve expat's shared object without relying on
        # LD_LIBRARY_PATH; libtool rewrites rpaths at install time.
        env.append("LDFLAGS",
                   f"-L{la} -Wl,-rpath,{la} "
                   f"-L{os.path.join(glib, 'lib')} "
                   f"-Wl,-rpath,{os.path.join(glib, 'lib')}")
        env.define("DBUS_CFLAGS",
                   f"-I{os.path.join(dbus, 'include')} "
                   f"-I{os.path.join(dbus, 'include', 'dbus-1.0')}")
        env.define("DBUS_LIBS", f"-L{la} -ldbus-1 -lexpat")
        env.define("GLIB_CFLAGS",
                   f"-I{os.path.join(glib, 'include', 'glib-2.0')} "
                   f"-I{os.path.join(glib, 'lib', 'glib-2.0', 'include')}")
        # glib/2.84.0.1 ships shared objects only, so the la-free static
        # archive directory cannot satisfy these -l names; the in-tree
        # dbus-gmain check programs link through GLIB_LIBS and failed with
        # "unable to find library -lgio-2.0". Point at glib's own libdir:
        # its shared objects carry their DT_NEEDED entries, so the static
        # glib inputs (-lintl -lffi -lpcre2-* -lz) are no longer needed.
        env.define(
            "GLIB_LIBS",
            f"-L{os.path.join(glib, 'lib')} -L{la} -lgio-2.0 -lgobject-2.0 "
            "-lgthread-2.0 -lgmodule-2.0 -lglib-2.0")
        # configure resolves glib-genmarshal through PKG_CHECK_VAR; the
        # generated glib-2.0.pc drops the custom variable, so pin it.
        env.define("GLIB_GENMARSHAL",
                   os.path.join(glib, "bin", "glib-genmarshal"))
        # HMDFS timestamp granularity can falsely trigger autotools
        # re-maintenance rules (am--refresh); the shipped Makefile.in is
        # valid, so neutralize regeneration for OHOS builds (avahi-glib
        # precedent, CI-proven).
        if str(self.settings.os) == "OHOS":
            env.define("ACLOCAL", "true")
            env.define("AUTOMAKE", "true")
            env.define("AUTOCONF", "true")
        # AC_CHECK_LIB(expat) bypasses pkg-config: expat ships only a
        # shared object on OHOS; its libdir above covers the link test
        # and consumers resolve it at runtime through the package graph.
        env.vars(self, scope="build").save_script("dbus-glib-deps")

    def build(self):
        apply_conandata_patches(self)

        # E236 scoped-la-free-static-archive-directory: copy only the
        # dependency .a files into a build-private directory that
        # contains no .la metadata. Never mutate the conan cache.
        # expat ships only a shared object on OHOS: it goes to the same
        # directory (still .la-free) so the single -L above satisfies
        # AC_CHECK_LIB(expat) and the build-time rpath.
        la = self._la_free_dir
        for dep in ("glib", "dbus", "pcre2"):
            libdir = os.path.join(self.dependencies[dep].package_folder, "lib")
            copy(self, "*.a", src=libdir, dst=la, keep_path=False)
        copy(self, "libexpat.so*",
             src=os.path.join(self.dependencies["expat"].package_folder, "lib"),
             dst=la, keep_path=False)
        self.output.info(f"la-free archives: {sorted(os.listdir(la))}")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # E236: remove generated .la metadata from the final package.
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "share", "gtk-doc"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "dbus-glib-1")
        self.cpp_info.libs = ["dbus-glib-1"]
        self.cpp_info.includedirs = ["include",
                                     os.path.join("include", "dbus-1.0")]
        self.cpp_info.bindirs = ["bin"]
        # Static consumers transitively need the glib headers/libs that
        # dbus-glib.h and dbus-glib-1.a reference; glib's CMakeDeps
        # targets are components and the aggregate target does not carry
        # their include dirs (E216), so pin the exact components.
        # Component refs: "pkg::component" for glib components; plain
        # dependencies expose their root as "pkg::pkg" (conan's implicit
        # single-component name). Bare "pkg" would be parsed as an
        # internal component of this package (conan 2.29 behavior).
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gthread-2.0",
            "glib::gmodule-2.0",
            "glib::gio-2.0",
            "dbus::dbus",
            # expat is deliberately not listed: it is declared as an
            # override (the alignment pin that lets gtk3 and dbus-glib
            # share one graph), and conan rejects cpp_info.requires
            # entries for packages that are not direct requirements. Its
            # link input reaches pkg-config consumers through the
            # generated .pc file; the repo's other dbus+expat recipes
            # (audtty, avahi-*, awf-gtk, libkysdk-base) do the same.
            # Part of the final static link line of libdbus-glib-1.a.
            "pcre2::pcre2",
        ]
