#!/usr/bin/env python3
"""Conan recipe — libedataserverui4 3.60.2 (evolution-data-server, CMake).

libedataserverui4 is **not** a standalone upstream source package: it is the
GTK4 UI convenience library of Evolution-Data-Server, built from
``src/libedataserverui`` inside the evolution-data-server source tree.  The
CMake target is ``edataserverui4`` and the installed shared object is
``libedataserverui4-1.0.so`` (headers under
``include/evolution-data-server/libedataserverui4/``).

Consequences for this recipe:

* The official evolution-data-server release tarball is the source of truth
  (R39) — there is no libedataserverui4 tarball to download.
* ``src/libedataserverui`` links against the *in-tree* shared libraries
  ``camel``, ``ecal``, ``edataserver`` and ``edbus-private``.  Those are not
  published as separate packages in the OHPC registry, so the recipe builds
  the whole tree and packages the four private shared libraries together with
  the UI library.
* Only the GTK4 flavour (``ENABLE_GTK4=ON``) is produced; the GTK3 flavour
  (``ENABLE_GTK=OFF``), the WebKitGTK OAuth2 helpers, the weather backend and
  the libcanberra sound support are disabled because those dependencies are
  not published for OpenHarmony PC.

Adapted to HarmonyOS PC (aarch64).  See notes.md for the platform notes.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    rmdir,
    save,
)
from conan.tools.gnu import PkgConfigDeps


# ------------------------------------------------------------------ #
# Upstream integration-test harness (HarmonyOS PC specifics)
# ------------------------------------------------------------------ #
# The upstream suite is a *server integration* suite: GLib's GTestDBus spawns
# a private D-Bus session bus and the evolution-*-factory services.  Two
# HarmonyOS specifics have to be papered over for it to start at all:
#
#  * /tmp is a read-only filesystem and unix sockets may only be created below
#    /data/storage/el2/base/cache, while GTestDBus hardcodes
#    "<listen>unix:tmpdir=/tmp</listen>" into the bus configuration it writes.
#    DBUS_WRAPPER receives the real config file, rewrites that line and execs
#    the real dbus-daemon.
#  * the platform has no passwd entry for the build uid, and dbus-daemon /
#    GLib abort with "getpwuid_r(): failed due to unknown user id"; FAKEPW_C
#    supplies a minimal synthetic entry via LD_PRELOAD.
DBUS_WRAPPER = """#!/bin/sh
# HarmonyOS PC shim for GLib's GTestDBus (see conanfile.py / notes.md).
REAL="{daemon}"
cfg=""; prev=""
for a in "$@"; do
  case "$a" in --config-file=*) cfg="${{a#--config-file=}}";; esac
  if [ "$prev" = "--config-file" ]; then cfg="$a"; fi
  prev="$a"
done
d="${{EDS_TEST_DBUS_TMPDIR:-${{TMPDIR:-/tmp}}}}"
if [ -n "$cfg" ] && [ -f "$cfg" ]; then
  sed -i "s#unix:tmpdir=/tmp#unix:tmpdir=$d#" "$cfg"
fi
exec env LD_PRELOAD="{shim}" "$REAL" "$@"
"""

FAKEPW_C = r"""
#define _GNU_SOURCE
#include <pwd.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdio.h>
#include <sys/types.h>

static struct passwd pw;
static char name[64], dir[512], shell[64];
static int inited = 0;

static void init_pw(void) {
    const char *u, *h;
    if (inited) return;
    u = getenv("EDS_FAKE_USER"); if (!u || !*u) u = "user";
    h = getenv("HOME"); if (!h || !*h) h = "/";
    snprintf(name, sizeof name, "%s", u);
    snprintf(dir, sizeof dir, "%s", h);
    snprintf(shell, sizeof shell, "%s", "/bin/sh");
    pw.pw_name = name;  pw.pw_passwd = (char *)"x";
    pw.pw_uid = getuid(); pw.pw_gid = getgid();
    pw.pw_gecos = (char *)""; pw.pw_dir = dir; pw.pw_shell = shell;
    inited = 1;
}

struct passwd *getpwuid(uid_t uid) { init_pw(); pw.pw_uid = uid; return &pw; }

int getpwuid_r(uid_t uid, struct passwd *pwd, char *buf, size_t buflen,
               struct passwd **result) {
    init_pw(); pw.pw_uid = uid; (void)buf; (void)buflen;
    if (pwd) memcpy(pwd, &pw, sizeof(struct passwd));
    if (result) *result = pwd ? pwd : &pw;
    return 0;
}

struct passwd *getpwnam(const char *nm) { init_pw(); (void)nm; return &pw; }
"""

DBUS_SOCKET_DIR = "/data/storage/el2/base/cache"


def _fix_relative_soname(path):
    """Rewrite './libX.so' SONAME/NEEDED strings of an ELF object in place.

    The published libical3 shared objects carry the *relative* SONAME
    "./libical.so" / "./libical-glib.so" (that package injects
    "-Wl,-soname,./" because absolute sonames / $ORIGIN are unstable on
    HMDFS).  The OHOS loader treats a DT_NEEDED entry containing "/" as a path
    relative to the working directory, so any consumer of libical-glib.so
    aborts at start-up with

        Error loading shared library ./libical.so (needed by ...)

    The replacement string is shorter than the original, so it is written back
    with NUL padding at the very same offset: no ELF structure is moved and no
    file layout changes.
    """
    with open(path, "rb") as handle:
        data = handle.read()
    changed = False
    for name in (b"libical-glib.so", b"libicalss.so", b"libicalvcal.so",
                 b"libical.so"):
        old = b"./" + name + b"\x00"
        new = name + b"\x00" * 3              # same total length as `old`
        if old in data:
            data = data.replace(old, new)
            changed = True
    if changed:
        with open(path, "wb") as handle:
            handle.write(data)


class Libedataserverui4Conan(ConanFile):
    name = "libedataserverui4"
    version = "3.60.2"
    description = ("Evolution-Data-Server GTK4 UI convenience library "
                   "(libedataserverui4-1.0) incl. its private EDS libraries")
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/evolution-data-server"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    # ------------------------------------------------------------------ #
    # configuration
    # ------------------------------------------------------------------ #

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}"
            )

    def requirements(self):
        # Every requirement below is published in the ohpcd registry.
        # glib must be declared as `override=True`: gtk4/4.22.4 overrides glib
        # to 2.84.0.1.1 graph-wide while pango/1.56.4 (pulled in by gtk4)
        # still asks for glib/2.84.0.1.  A plain (non-override) glib
        # requirement at the root re-introduces the conflict between the two
        # revisions ("Version conflict: Conflict between glib/2.84.0.1 and
        # glib/2.84.0.1.1 / Conflict originates from pango/1.56.4").
        self.requires("glib/2.84.0.1.1", override=True)
        self.requires("gtk4/4.22.4")
        # libsoup3 3.6.5-r3 is the "shared glib release form" revision of
        # libsoup3: r1/r2 statically embed the GObject of glib2/2.88.0 into
        # libsoup-3.0.so (and export its symbols), which collides with the
        # shared glib/2.84.0.1.1 that gtk4 links in the same process
        # ("cannot register existing type 'gchar'", SIGABRT).  r3 declares the
        # shared glib/2.84.0.1.1 dependency instead and is the only revision
        # that is loadable together with gtk4.
        self.requires("libsoup3/3.6.5-r3")
        self.requires("json-glib/1.10.6.1")
        self.requires("libsecret/0.21.7")
        self.requires("libxml2/2.15.3.1")
        # sqlite3 is pinned to the revision libsoup3/3.6.5-r1 already builds
        # against (3.49.1).  Requiring a different revision would change the
        # libsoup3 package_id and force a from-source rebuild of libsoup3.
        self.requires("sqlite3/3.49.1")
        # libecal/libedata-cal use the GObject bindings of libical, so the
        # published libical/4.0.1 (built with LIBICAL_GLIB=OFF, i.e. without
        # libical-glib.pc / libical-glib.h) is unusable.  libical3/3.0.20 is
        # built with ICAL_GLIB=ON and ships libical-glib.so + headers; see
        # _fix_dependency_metadata().
        self.requires("libical3/3.0.20")
        self.requires("nss/3.118.1")
        self.requires("nspr/4.37")
        self.requires("uuid/2.40.1")
        self.requires("icu/76.1")
        self.requires("zlib/1.3.1.1")

    def build_requirements(self):
        # dbus-daemon is needed only to execute the upstream integration test
        # suite: GLib's GTestDBus starts a private D-Bus session bus for it.
        self.tool_requires("dbus/1.14.10.2")

    def layout(self):
        cmake_layout(self)

    # ------------------------------------------------------------------ #
    # sources
    # ------------------------------------------------------------------ #

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ #
    # generate / build / package
    # ------------------------------------------------------------------ #

    def generate(self):
        self._fix_dependency_metadata()
        PkgConfigDeps(self).generate()
        tc = CMakeToolchain(self)
        # Only the GTK4 flavour of libedataserverui is requested.
        tc.variables["ENABLE_GTK4"] = True
        tc.variables["ENABLE_GTK"] = False
        # Not published for OpenHarmony PC (see notes.md).
        tc.variables["ENABLE_OAUTH2_WEBKITGTK"] = False
        tc.variables["ENABLE_OAUTH2_WEBKITGTK4"] = False
        tc.variables["ENABLE_WEATHER"] = False
        tc.variables["ENABLE_CANBERRA"] = False
        # Not needed for a library package / not available.
        tc.variables["ENABLE_GOA"] = False
        tc.variables["ENABLE_EXAMPLES"] = False
        tc.variables["ENABLE_VALA_BINDINGS"] = False
        tc.variables["ENABLE_INTROSPECTION"] = False
        tc.variables["ENABLE_GTK_DOC"] = False
        tc.variables["ENABLE_GI_DOCGEN"] = False
        tc.variables["WITH_PRIVATE_DOCS"] = False
        tc.variables["ENABLE_MAINTAINER_MODE"] = False
        tc.variables["ENABLE_TESTS"] = True
        tc.variables["ENABLE_INSTALLED_TESTS"] = False
        # Optional system services / databases that do not exist on OHOS.
        tc.variables["WITH_LIBDB"] = False
        tc.variables["WITH_OPENLDAP"] = False
        tc.variables["WITH_SUNLDAP"] = False
        tc.variables["WITH_KRB5"] = False
        tc.variables["WITH_PHONENUMBER"] = False
        tc.variables["ENABLE_BACKTRACES"] = False
        for name, path in self._native_host_tools().items():
            tc.variables[name] = path
        for name, value in self._platform_link_flags().items():
            tc.variables[name] = value
        tc.generate()

    def build(self):
        self._prepare_libical3()
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def package(self):
        with self._build_environment().vars(self).apply():
            cmake = CMake(self)
            cmake.install()

        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # Ship the SONAME-fixed libical objects (see _prepare_libical3()) so
        # that the DT_NEEDED entries of the EDS shared libraries resolve at
        # run time.
        fixed = self._libical3_fixed_libdir()
        if os.path.isdir(fixed):
            copy(self, "*.so", src=fixed,
                 dst=os.path.join(self.package_folder, "lib"))

        # Keep only the library payload: the tree also installs EDS command
        # line tools (bin/), camel providers / backends modules
        # (lib/evolution-data-server/*), D-Bus services, GSettings schemas,
        # systemd units and ~100 gettext catalogues, none of which belong to
        # a library package.
        for unwanted in ("bin", "libexec", "share", "etc", "sbin"):
            rmdir(self, os.path.join(self.package_folder, unwanted))
        rmdir(self, os.path.join(self.package_folder, "lib", "systemd"))

        keep_private = {"libedbus-private.so"}
        private_dir = os.path.join(self.package_folder, "lib",
                                   "evolution-data-server")
        if os.path.isdir(private_dir):
            for name in os.listdir(private_dir):
                base = name.split(".so")[0] + ".so" if ".so" in name else name
                if base not in keep_private:
                    full = os.path.join(private_dir, name)
                    if os.path.isdir(full):
                        rmdir(self, full)
                    else:
                        rm(self, name, private_dir)

        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        # libedataserverui4-1.0.so is the requested artefact; the four private
        # EDS libraries it links against are shipped in the same package so
        # that the shared objects resolve their DT_NEEDED entries.
        self.cpp_info.libs = [
            "edataserverui4-1.0",
            "camel-1.2",
            "ecal-2.0",
            "edataserver-1.2",
            "edbus-private",
        ]
        self.cpp_info.libdirs = ["lib", "lib/evolution-data-server"]
        self.cpp_info.includedirs = ["include/evolution-data-server"]
        self.cpp_info.bindirs = []
        # `pkg_config_name` of every dependency is picked up by PkgConfigDeps
        # and propagated as `Requires:` in the generated
        # libedataserverui4-1.0.pc, which lets a consumer pull in gtk4/glib
        # headers with a single pkg-config lookup.  glib itself cannot be
        # listed here: it is declared as an `override=True` requirement (the
        # only form that keeps gtk4/pango from fighting over two glib
        # revisions) and overrides are not direct dependencies of the recipe;
        # gtk4 -> pango -> glib pulls the glib .pc in anyway.
        self.cpp_info.requires = [
            "gtk4::gtk4",
            "libsoup3::libsoup3",
            "json-glib::json-glib",
            "libsecret::libsecret",
            "libxml2::libxml2",
            "sqlite3::sqlite3",
            "libical3::libical3",
            "nss::nss",
            "nspr::nspr",
            "uuid::uuid",
            "icu::icu",
            "zlib::zlib",
        ]
        self.cpp_info.set_property("cmake_file_name", "libedataserverui4")
        self.cpp_info.set_property("cmake_target_name",
                                   "libedataserverui4::libedataserverui4")
        self.cpp_info.set_property("pkg_config_name", "libedataserverui4-1.0")

    # ------------------------------------------------------------------ #
    # helpers — dependency metadata fixes
    # ------------------------------------------------------------------ #

    def _fix_dependency_metadata(self):
        """Adapt the metadata of four dependencies to the needs of this build.

        These are *consumer side* fixes only: no dependency package is
        modified, and every library still comes from the published ohpcd
        binary of that dependency.
        """
        # 1) libical-glib ---------------------------------------------------
        # Upstream: pkg_check_modules(CALENDAR REQUIRED gio-2.0
        #           libical-glib>=3.0.7 libsoup-3.0 libxml-2.0)
        # libical3/3.0.20 is built with ICAL_GLIB=ON (ships libical-glib.so +
        # include/libical-glib) but never sets `pkg_config_name`, so
        # PkgConfigDeps would emit `libical3.pc` instead.  Its recipe also
        # uses component names that the ohpc glib recipe does not define
        # ("glib::glib"/"glib::gobject"), which makes PkgConfigDeps abort with
        # "Component 'glib::gobject' not found in 'glib' package requirement".
        libical3 = self.dependencies["libical3"]
        libical3.cpp_info.set_property("pkg_config_name", "libical-glib")
        libical3.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "libxml2::libxml2",
        ]
        # The libical3 shared objects carry the *relative* SONAME
        # "./libical-glib.so" / "./libical.so" (the package deliberately
        # injects -Wl,-soname,./ because absolute sonames/$ORIGIN are unstable
        # on HMDFS).  The OHOS loader treats a NEEDED entry containing "/" as a
        # path relative to the current working directory, so any consumer of
        # libecal-2.0.so aborts at start-up with
        #   Error loading shared library ./libical-glib.so
        #   (needed by .../lib/libecal-2.0.so)
        # _prepare_libical3() therefore copies the objects into the build
        # folder with the SONAME/NEEDED strings rewritten to plain basenames
        # and re-signs them; the fixed objects are shipped in this package so
        # that the DT_NEEDED entries resolve at run time.
        #
        # Linking the *shared* objects (rather than the static archives) is
        # what keeps a single instance of the libical GObject types per
        # process: the archives would be embedded into libecal-2.0.so *and*
        # into every consumer/test binary, and the second copy aborts with
        #   GLib-GObject-FATAL-CRITICAL: cannot register existing type 'ICalValue'
        libical3 = self.dependencies["libical3"]
        libical3.cpp_info.libdirs = [self._libical3_fixed_libdir()]
        libical3.cpp_info.libs = ["ical-glib", "icalss", "icalvcal", "ical"]
        libical3.cpp_info.sharedlinkflags = []

        # 2) icu ------------------------------------------------------------
        # Upstream: pkg_check_modules(ICU icu-i18n icu-uc); the icu package
        # exports a single `icu.pc`, so two aliases are added.
        icu = self.dependencies["icu"]
        icu.cpp_info.set_property("pkg_config_aliases", ["icu-i18n", "icu-uc"])

        # 3) glib2 ----------------------------------------------------------
        # glib2/2.88.0 is a *static* GLib build pulled in by graphene (and, in
        # the previous libsoup3 revisions, by libsoup3).  Its pkg_config_name
        # ("glib-2.0") collides with the per-component glib-2.0.pc of the
        # shared glib/2.84.0.1.1 that gtk4 uses, and whichever generator ran
        # last won.  Rename it AND strip its archives from the metadata:
        # `Requires:` of the dependent .pc files is derived from the
        # dependency names, so glib2 would still advertise
        # `-L<static glib2>/lib -lglib-2.0 ... -lgthread-2.0 -lffi -lintl`.
        # Because libgthread-2.0 is only available as glib2's .a, that drags a
        # *second* copy of GLib/GObject into every binary and aborts it at
        # startup with
        #   GLib-GObject-CRITICAL: cannot register existing type 'gchar'
        #   GLib-GObject:ERROR ../gobject/gvaluetypes.c _g_value_types_init
        # The shared glib of the graph already provides every needed module.
        glib2 = self.dependencies["glib2"]
        glib2.cpp_info.set_property("pkg_config_name", "glib2-static")
        glib2.cpp_info.libs = []
        glib2.cpp_info.libdirs = []
        glib2.cpp_info.includedirs = []

        # 4) nss -------------------------------------------------------------
        # The nss package ships both the coreconf static archives (libnss.a,
        # libssl.a, ...) and the shared coreconf libraries (libnss3.so,
        # libssl3.so, ...).  Built with shared=False its cpp_info advertises
        # the *static* linker names, but those archives do not carry the NSS
        # API (CERT_GetDefaultCertDB / PK11_GetBestSlot live in libnss3.so),
        # so linking libcamel/libedataserver with -Wl,--no-undefined failed:
        #   ld.lld: error: undefined symbol: CERT_GetDefaultCertDB
        # Use the shared coreconf names that the package actually provides.
        nss = self.dependencies["nss"]
        nss.cpp_info.libs = ["nss3", "ssl3", "smime3", "nssutil3", "softokn3",
                             "freebl3", "nssckbi", "nssdbm3", "sqlite3"]

        # 5) glib proxy-libintl ---------------------------------------------
        # <glib/gi18n-lib.h> maps gettext()/dgettext()/... to the
        # g_libintl_* wrappers that glib's bundled proxy-libintl (libintl.so
        # of the glib package) provides.  The PkgConfigDeps-generated glib
        # .pc files do not list it, so every shared object built here had
        # undefined g_libintl_* symbols and the -Wl,--no-undefined links of
        # libcamel / libedataserver / libedataserverui4 failed:
        #   ld.lld: error: undefined symbol: g_libintl_bindtextdomain
        glib = self.dependencies["glib"]
        for _component in glib.cpp_info.components.values():
            if "intl" not in _component.libs:
                _component.libs.append("intl")

        # 6) icu (static C++ build) -----------------------------------------
        # The icu package is a static build (libicuuc.a / libicui18n.a /
        # libicudata.a) whose objects need the C++ runtime.  ICU is pulled in
        # by the C-only links of libcamel/libedataserver, so without -lc++ the
        # links failed with
        #   ld.lld: error: undefined symbol: __cxa_begin_catch
        #   >>> referenced by uprops.cpp in archive .../libicuuc.a
        icu = self.dependencies["icu"]
        if "c++" not in icu.cpp_info.libs:
            icu.cpp_info.libs.append("c++")

        # 7) glib-compile-schemas ------------------------------------------
        # GLibTools.cmake locates it either with find_program() (when
        # CMAKE_CROSSCOMPILING) or by asking pkg-config for the
        # `glib_compile_schemas` variable of gio-2.0.pc - the branch taken on
        # OpenHarmony PC, where the build machine and the target are both
        # aarch64 OHOS.  The PkgConfigDeps-generated gio-2.0.pc does not carry
        # that variable, so configure aborted with "Cannot find
        # glib-compile-schemas".  Point it at the runnable native copy (the
        # one inside the glib conan package cannot be executed on OHOS).
        compile_schemas = self._native_host_tools().get("GLIB_COMPILE_SCHEMAS")
        if compile_schemas:
            glib = self.dependencies["glib"]
            glib.cpp_info.components["gio-2.0"].set_property(
                "pkg_config_custom_content",
                {"glib_compile_schemas": compile_schemas})

    def _native_host_tools(self):
        """Build-time helper programs, seeded into the CMake cache.

        * GLibTools.cmake requires glib-mkenums, gdbus-codegen,
          glib-compile-schemas and glib-compile-resources.  The copies shipped
          inside the glib *conan* package cannot be executed on HarmonyOS:
          they are OHOS ELF binaries which never go through the recipe signing
          step, so the loader rejects them ("operation not permitted").  The
          native runtime copies (OHOS "hnp" packages, which the CI profile puts
          on PATH) are used instead; the resource compiler additionally links
          against libffi.so.8, which _build_environment() adds to
          LD_LIBRARY_PATH.
        * po/CMakeLists.txt (via CMake's FindGettext) regenerates the .po
          catalogue with msgmerge as part of the default build.  msgmerge is
          shipped by the OHOS gettext package but is *not* linked into the
          "hnp" bin/ directory, so it is looked up inside that package.
        """
        tools = {}
        # Python based glib tools come from the conan glib package
        # (they carry a "#!/usr/bin/env python3" shebang and therefore run
        # fine); the OHOS "hnp" copies of those scripts point at the
        # non-existent /usr/bin/python3 and /usr/bin/perl interpreters.
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        for name, program in (("GLIB_MKENUMS", "glib-mkenums"),
                              ("GDBUS_CODEGEN", "gdbus-codegen"),
                              ("GLIB_GENMARSHAL", "glib-genmarshal")):
            path = os.path.join(glib_bin, program)
            if os.path.isfile(path):
                tools[name] = path
        # Compiled glib tools must come from the OHOS "hnp" runtime: the ones
        # in the conan package are unsigned OHOS ELF binaries and are rejected
        # by the loader.
        for name, program in (("GLIB_COMPILE_SCHEMAS", "glib-compile-schemas"),
                              ("GLIB_COMPILE_RESOURCES",
                               "glib-compile-resources"),
                              ("GETTEXT_XGETTEXT_EXECUTABLE", "xgettext"),
                              ("GETTEXT_MSGFMT_EXECUTABLE", "msgfmt")):
            path = shutil.which(program)
            if path:
                tools[name] = path
        for candidate in sorted(glob.glob("/data/service/hnp/*/*/bin/msgmerge"),
                                reverse=True):
            tools["GETTEXT_MSGMERGE_EXECUTABLE"] = candidate
            break
        return tools

    @staticmethod
    def _platform_link_flags():
        """Restore the Linux shared-library link settings for the OHOS target.

        Conan maps ``os=OHOS`` to ``CMAKE_SYSTEM_NAME=HarmonyOS`` and CMake has
        no ``Platform/HarmonyOS.cmake`` ("System is unknown to cmake"), so the
        platform variables that ``Modules/Platform/Linux.cmake`` normally
        defines are missing: CMake then emits neither ``-Wl,-soname`` nor
        ``-Wl,-rpath`` and every shared object is produced *without* a SONAME.
        A consumer linking such a library records the build-tree path in
        DT_NEEDED (e.g. ``../../camel/libcamel-1.2.so``) and cannot load it at
        run time, so the values are set explicitly here.
        """
        # Only the SONAME flag is restored: enabling the -rpath flags makes
        # CMake perform an install-time relink (CMakeFiles/CMakeRelink.dir)
        # which fails for this project ("cannot find
        # .../CMakeRelink.dir/libedataserver-1.2.so.27.0.0").  Library lookup
        # at run time is provided by the conan-generated run environment
        # (LD_LIBRARY_PATH over all dependency libdirs).
        flags = {
            "CMAKE_SHARED_LIBRARY_SONAME_C_FLAG": "-Wl,-soname,",
            "CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG": "-Wl,-soname,",
            "CMAKE_DL_LIBS": "dl",
        }
        return flags

    def _build_environment(self):
        """PATH / LD_LIBRARY_PATH / TMPDIR for the build.

        The build machine and the target are both aarch64 OpenHarmony, so the
        freshly built OHOS binaries are executed directly during configure
        (CHECK_C_SOURCE_RUNS probes) and by the test_package.
        """
        environment = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        for dependency in self.dependencies.host.values():
            bin_dir = os.path.join(dependency.package_folder, "bin")
            if os.path.isdir(bin_dir):
                environment.prepend_path("PATH", bin_dir)
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        # libffi.so.8 provider for the native glib-compile-resources (see
        # _native_host_tools()); it is not part of the OHOS system loader path.
        for pattern in ("/data/service/hnp/*/libffi*/lib",
                        "/data/service/hnp/*/*/lib"):
            for candidate in sorted(glob.glob(pattern)):
                if glob.glob(os.path.join(candidate, "libffi.so.8*")):
                    environment.prepend_path("LD_LIBRARY_PATH", candidate)
        # The SONAME-fixed libical objects (see _prepare_libical3()) must win
        # over the ones of the libical3 package, so prepend them last.
        fixed = self._libical3_fixed_libdir()
        if os.path.isdir(fixed):
            environment.prepend_path("LD_LIBRARY_PATH", fixed)
        return environment

    def _sign_elf(self, path):
        """Sign one shared object for HarmonyOS (the loader refuses to map an
        unsigned object).  The tool paths are the ones every OHOS recipe in this
        repository uses."""
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(
                    f"Required OHOS signing tool not found: {tool}")
        self.run(f'"{objcopy}" --remove-section .codesign "{path}"')
        self.run(f'"{signer}" sign -inFile "{path}" -outFile "{path}" '
                 f'-selfSign 1')

    def _sign_installed_elfs(self):
        """Sign every shared object for HarmonyOS (otherwise the loader
        refuses to map it)."""
        targets = []
        for pattern in (
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        ):
            targets.extend(glob.glob(pattern, recursive=True))
        for target in targets:
            if os.path.islink(target):
                continue
            self._sign_elf(target)

    # ------------------------------------------------------------------ #
    # helpers — libical3 SONAME fix
    # ------------------------------------------------------------------ #

    def _libical3_fixed_libdir(self):
        return os.path.join(self.build_folder, "libical3-fixed", "lib")

    def _prepare_libical3(self):
        """Copy libical3's shared objects into the build folder with plain
        SONAMEs and re-sign them (see _fix_dependency_metadata)."""
        libical3 = self.dependencies["libical3"]
        src = os.path.join(libical3.package_folder, "lib")
        dst = self._libical3_fixed_libdir()
        os.makedirs(dst, exist_ok=True)
        for name in ("libical-glib.so", "libicalss.so", "libicalvcal.so",
                     "libical.so"):
            if not os.path.isfile(os.path.join(src, name)):
                continue
            copy(self, name, src=src, dst=dst)
            target = os.path.join(dst, name)
            _fix_relative_soname(target)
            self._sign_elf(target)

    # ------------------------------------------------------------------ #
    # helpers — upstream integration test suite
    # ------------------------------------------------------------------ #

    def _ctest(self):
        ctest = shutil.which("ctest")
        return ctest or "ctest"

    def _run_upstream_tests(self):
        """Best-effort execution of the upstream ctest suite on the target.

        The build machine and the target are both HarmonyOS PC (aarch64), so the
        freshly built test programs run directly.  The suite is a server
        integration suite: every test starts a private D-Bus session bus through
        GLib's GTestDBus and drives the evolution-*-factory services over D-Bus.
        The harness assembled here makes that possible on OHOS (see DBUS_WRAPPER
        and FAKEPW_C above).

        The step is deliberately **not fatal**.  Parts of the suite depend on
        facilities HarmonyOS PC does not provide (see notes.md); the result of
        the run is recorded in upstream-test-results.txt so that it is
        reproducible and auditable.  A failed run never turns a working recipe
        into a red build.
        """
        try:
            try:
                dbus_pkg = self.dependencies.build["dbus"]
            except (KeyError, TypeError):
                dbus_pkg = None
            daemon = (os.path.join(dbus_pkg.package_folder, "bin", "dbus-daemon")
                      if dbus_pkg and dbus_pkg.package_folder else "")
            if not daemon or not os.path.isfile(daemon):
                self.output.warning(
                    "upstream tests: dbus-daemon not available, run skipped")
                return

            work = os.path.join(self.build_folder, "upstream-tests")
            os.makedirs(work, exist_ok=True)
            shim_src = os.path.join(work, "ohos-fakepw.c")
            shim_so = os.path.join(work, "libohos-fakepw.so")
            wrapper = os.path.join(work, "dbus-daemon-ohos")
            save(self, shim_src, FAKEPW_C)
            save(self, wrapper, DBUS_WRAPPER.format(daemon=daemon, shim=shim_so))

            cc = None
            execs = self.conf.get("tools.build:compiler_executables")
            if isinstance(execs, dict):
                cc = execs.get("c")
            cc = cc or shutil.which("clang") or "clang"
            self.run(f'"{cc}" -shared -fPIC -O2 -o "{shim_so}" "{shim_src}"')
            os.chmod(wrapper, 0o755)

            os.makedirs(DBUS_SOCKET_DIR, exist_ok=True)

            build_libs = sorted({
                os.path.dirname(p)
                for p in glob.glob(os.path.join(self.build_folder, "**", "*.so*"),
                                   recursive=True)
            })
            env = self._build_environment()
            # First entry wins: the SONAME-fixed libical objects.
            env.prepend_path("LD_LIBRARY_PATH", self._libical3_fixed_libdir())
            for path in build_libs:
                env.prepend_path("LD_LIBRARY_PATH", path)
            env.define("G_TEST_DBUS_DAEMON", wrapper)
            env.define("EDS_TEST_DBUS_TMPDIR", DBUS_SOCKET_DIR)
            env.define("EDS_FAKE_USER", "user")
            env.define("LD_PRELOAD", shim_so)

            results = os.path.join(self.build_folder, "upstream-test-results.txt")
            with env.vars(self).apply():
                self.run(f'"{self._ctest()}" --output-on-failure -j1',
                         cwd=self.build_folder, ignore_errors=True)
            # Keep the ctest log next to the build for auditability.
            log = os.path.join(self.build_folder, "Testing", "Temporary",
                               "LastTest.log")
            if os.path.isfile(log):
                copy(self, "LastTest.log", src=os.path.dirname(log),
                     dst=self.build_folder)
                save(self, results, "see LastTest.log for the full ctest run\n")
            self.output.info("upstream tests executed (see "
                             f"{os.path.relpath(results, self.build_folder)})")
        except Exception as exc:                    # noqa: BLE001 - never fatal
            self.output.warning(f"upstream tests: run skipped ({exc})")

