#!/usr/bin/env python3
"""Conan recipe — m17n-lib 1.8.6 core library (libm17n-core) for HarmonyOS PC.

Upstream project : GNU m17n-lib — multilingual text handling (M-text) library
Upstream tarball : m17n-lib-1.8.6.tar.gz (savannah.gnu.org, official release)
Adapted target   : os=OHOS, arch=armv8 (aarch64), clang 15

The task deliverable is the core library ``libm17n-core.so``.  Upstream builds
libm17n-core.so / libm17n.so / libm17n-flt.so from one configure+make run in a
single source tree (src/Makefile.am: BASICBUILDS), and the latter two are
useless without the core, so all three non-GUI libraries are packaged together.
The GUI level (libm17n-gui + the libm17n-X / libm17n-gd / libmimx-* modules) is
compiled by upstream's unconditional GUI block and excluded from the package.

Platform notes
--------------
* ``--disable-nls`` — the OHOS sysroot ships an *empty* ``<libintl.h>`` stub and
  no libintl provider, while the device's ``libintl.so.8.proxy`` renames the
  GNU gettext entry points (``g_libintl_*``).  Upstream guards every gettext
  call with ``#if ENABLE_NLS`` (src/internal.h, src/m17n-core.c, src/input.c),
  so building with NLS disabled removes the dependency entirely: the produced
  ``libm17n-core.so`` has no ``libintl`` entry in DT_NEEDED and cannot hit the
  runtime "libintl_dgettext: symbol not found" failure.
* GUI artifacts excluded — libm17n-gui and the libm17n-X / libm17n-gd /
  libmimx-* modules need X11/Xft/Xaw, freetype, fontconfig or libotf, none of
  which exist on OHOS.  Upstream cannot switch the GUI level off at configure
  time in this release (see generate()), so its artifacts are dropped in
  package().
* libxml2 is a hard requirement (the m17n database is XML based).  It comes
  from the registry as a normal host requirement; because the ``xml2-config``
  installed by that package reports a wrong prefix, configure is pointed at the
  requirement's real include/lib paths instead (see generate()).
* Two upstream patches (both portability-only, no source code touched):
  - ``patches/0001-config.guess-harmonyos.patch`` teaches the bundled
    config.guess (2024-07-27) the HarmonyOS system name, so configure can
    determine the build type natively instead of falling back to the dummy.c
    probe that the OHOS worker storage rejects.
  - ``patches/0002-configure-umask-hmdfs.patch`` creates configure's
    ``./confXXXXXX`` helper directory with umask 022 instead of 077; on the
    worker's HMDFS style storage a 0700 directory makes the generated helper
    scripts unusable ("subs1.awk: Permission denied").
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                               get, rm, rmdir)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class Libm17nCoreConan(ConanFile):
    name = "libm17n-core"
    version = "1.8.6"
    description = ("GNU m17n-lib core library: multilingual text handling "
                   "(M-text) for HarmonyOS PC")
    license = "LGPL-2.1-or-later"
    homepage = "https://www.nongnu.org/m17n/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} is adapted for Linux and OHOS only"
            )

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # libxml2 is mandatory for m17n-lib (database parsing).
        self.requires("libxml2/2.15.3.1")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # The dependency .pc files are only visible to configure when the
        # generators folder is on the pkg-config search path.
        PkgConfigDeps(self).generate()

        # Real include/lib paths of the libxml2 requirement (see the note on
        # xml2-config further down).
        dep_info = self.dependencies["libxml2"].cpp_info
        # src/configure.ac's libxml2 fallback branch adds "-lxml2 -lz -lpthread
        # -lm" to every library's LIBADD, so libz.so ends up in DT_NEEDED of the
        # produced .so files.  That is fine on OHOS: the SDK sysroot stub for the
        # base-system zlib carries SONAME "libz.so" (verified with readelf), so
        # the needs entry resolves on the device.
        ldflags = " ".join(f"-L{p}" for p in dep_info.libdirs
                           if os.path.isdir(p))
        cppflags = " ".join(f"-I{p}" for p in dep_info.includedirs
                            if os.path.isdir(p))

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-nls",
            "--disable-dependency-tracking",
            # AC_FUNC_MALLOC / AC_FUNC_REALLOC default to "broken" when their
            # test program cannot be run (cross building), which makes config.h
            # "#define malloc rpl_malloc" and breaks every compilation unit that
            # assigns through the macro (src/face.c: "incompatible integer to
            # pointer conversion ... from 'int'" — no rpl_malloc is provided).
            # Both glibc and the OHOS musl libc return a unique pointer for
            # malloc(0) / realloc(p, 0), so the answers are seeded instead of
            # letting the run test decide.
            "ac_cv_func_malloc_0_nonnull=yes",
            "ac_cv_func_realloc_0_nonnull=yes",
            "ac_cv_func_alloca_works=yes",
            "ac_cv_func_memcmp_working=yes",
            "ac_cv_func_strcoll_works=yes",
            # The xml2-config that ships inside libxml2/2.15.3.1 is a
            # configure-time artifact of *that* build: it hardcodes
            # prefix=/usr/local, so it reports "-I/usr/local/include/libxml2"
            # and "-L/usr/local/lib -lxml2 ...".  src/configure.ac feeds those
            # answers straight into its libxml2 probes, which then fail and the
            # library gets built *without* the XML database backend (HAVE_XML2
            # undefined) — a silently degraded package.  The program lookup is
            # skipped instead (AC_CHECK_PROG does not search when its variable
            # is preset) and the requirement's real paths are injected above, so
            # configure.ac's fallback branch (-lxml2 -lz -lpthread -lm) links
            # against the package taken from the registry.
            "HAVE_XML2_CONFIG=no",
        ])
        # NOTE: the GUI level cannot be disabled in this release.  Its guard in
        # configure.ac is AM_CONDITIONAL(WITH_GUI, test x$with_gui != xno) while
        # AC_ARG_ENABLE(gui, ...) only fills $enable_gui, so "--disable-gui" is
        # silently ignored; forcing with_gui=no aborts configure ("conditional
        # HAVE_PKG_CONFIG was never defined") because the GUI block is not
        # actually optional.  The GUI artifacts are therefore removed in
        # package() instead.
        if self.options.shared:
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")

        env = tc.environment()
        if cppflags:
            env.append("CPPFLAGS", cppflags)
        if ldflags:
            env.append("LDFLAGS", ldflags)
        # Restrict pkg-config to the generated .pc files of the declared
        # requirements: the OHOS base system is not a build dependency, and
        # autodetected host libraries (libthai/anthy/wordcut) must not leak into
        # the link line of a recipe that does not declare them.
        env.define("PKG_CONFIG_PATH", self.generators_folder)
        env.define("PKG_CONFIG_LIBDIR", self.generators_folder)
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])

        libdir = os.path.join(self.package_folder, "lib")
        incdir = os.path.join(self.package_folder, "include")

        # libtool archives burn the build-time libdir into consumer link lines;
        # conan builds with prefix "/" so they would point at "//lib/lib*.la".
        rm(self, "*.la", libdir, recursive=True)
        # bin/ only holds upstream's example programs (example/Makefile.am
        # bin_PROGRAMS: m17n-conv, m17n-date, m17n-dump, m17n-edit,
        # m17n-input-test, m17n-view); they need the m17n-db data package at run
        # time and are out of scope for this library package.
        rmdir(self, os.path.join(self.package_folder, "bin"))
        # The GUI level cannot be switched off in this release (see the note in
        # generate()), so its artifacts are dropped here: libm17n-gui and the
        # libm17n-X / libm17n-gd / libmimx-anthy / libmimx-ispell modules need
        # X11, freetype, fontconfig, libotf, anthy or ispell — none of which
        # exist on OHOS, and the modules would reference the removed
        # libm17n-gui.so.0.  What remains is the non-GUI library set this
        # package delivers.
        rm(self, "libm17n-gui*", libdir)
        rm(self, "m17n-gui.pc", os.path.join(libdir, "pkgconfig"))
        rmdir(self, os.path.join(libdir, "m17n"))
        rm(self, "m17n-gui.h", incdir)
        rm(self, "m17n-X.h", incdir)
        # Code signing must be the last step that touches the ELF bytes,
        # because the signature covers them (E135/E077/E489).
        self._sign_libraries()

    def _sign_libraries(self):
        """Code-sign the shipped shared libraries when the OHOS tools exist.

        HarmonyOS PC requires executables and dlopen()ed libraries to carry a
        valid signature; the signature is a hash over the file bytes, so it is
        applied after every other packaging step.  The tools only exist on the
        OHOS build worker, so this is a no-op on other machines.
        """
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            self.output.info("OHOS code-signing tools not present: skipping ELF signing")
            return
        for name in sorted(os.listdir(os.path.join(self.package_folder, "lib"))):
            path = os.path.join(self.package_folder, "lib", name)
            if not name.endswith(".so") and ".so." not in name:
                continue
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            self.run(f'{objcopy} --remove-section .codesign "{path}" '
                     f'2>/dev/null || true', ignore_errors=True)
            ret = self.run(f'{signer} sign -inFile "{path}" -outFile "{path}" '
                           f'-selfSign 1', ignore_errors=True)
            if ret != 0:
                self.output.warning(f"binary-sign-tool returned {ret} for {name}")

    def package_info(self):
        # Static consumers need dependants before dependencies; m17n and
        # m17n-flt both link against m17n-core.
        self.cpp_info.libs = ["m17n", "m17n-flt", "m17n-core"]
        self.cpp_info.set_property("cmake_file_name", "libm17n-core")
        self.cpp_info.set_property("cmake_target_name",
                                   "libm17n-core::libm17n-core")
        self.cpp_info.set_property("pkg_config_name", "m17n-core")
