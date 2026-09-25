#!/usr/bin/env python3
"""Conan recipe for xplc 0.3.13 — Cross-Platform Lightweight Components.

XPLC is a C++ component system (C core + C++ binding) with a hand-written
make build driven by an Autoconf 2.59 `configure`.  Adaptation points proven
on-device (evidence: $TASK_DIR/w0/w0-gates.md):

1. uuid — configure is dual-path: it probes `<uuid/uuid.h>` + `uuid_unparse`
   in -luuid and only falls back to the bundled `uuid/libuuid.a` when that
   probe fails.  The ohpcd archive `uuid/2.40.1` exports
   `include/uuid/uuid.h`, so `AutotoolsDeps` MUST be generated or the
   `AC_CHECK_LIB` probe runs without -I/-L (see
   notes/defects/conan-verify-and-recipe.md "AutotoolsDeps 缺失使 AC_CHECK_LIB
   假绿").  Its `uuid.pc` reports `Cflags: -I${includedir}/uuid` which does NOT
   match the source's `<uuid/uuid.h>` form — never take pkg-config --cflags.
2. `-Wno-c++11-narrowing` — `moduleloader.cpp:65` switches an `unsigned int`
   on `case -1:` under `-DUNSTABLE`; narrowing is an error from C++11 on, so
   downgrading to gnu++14 does NOT help (bcp precedent boundary) — the flag
   keeps compiler.cppstd=17.
3. `INSTALL=/bin/install` — PATH on this device has no `/bin`, so configure
   falls back to the 2000-era bundled `install-sh` which has **no multi-source
   loop** and installs 1 of 24 headers while `make install` still exits 0.
4. SONAME — 0.3.13 has odd minor=3 ⇒ upstream sets
   `SONAME=libxplc.so.0.3.13-unstable` but installs `libxplc.so.0.3.13`;
   consumers then fail at load time.  Fixed by symlinking the SONAME name.
5. `defines=["UNSTABLE"]` — `xplc.pc` does not carry `-DUNSTABLE` although the
   library is built with it, so headers expand to an out-of-line-in-class
   static member and consumer compiles fail.

NOTE: upstream has no shared/static switch at all — its default target always
emits both `.a` and `.so` — so `shared` here does NOT toggle a configure flag
(it would only change package_id).  Conan still *requires* the option once
`package_type = "library"` is declared (`Package type is 'library', but no
'shared' option declared`), and a52dec/0.7.4 declares it the same way.  Both
artefacts are always delivered: dropping the `.so` to dodge the broken SONAME
would be a functional regression, so the SONAME is repaired instead (item 4).
"""
import glob
import os
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XplcConan(ConanFile):
    name = "xplc"
    version = "0.3.13"
    description = "XPLC - Cross-Platform Lightweight Components (component system)"
    license = "LGPL-2.1-or-later"
    homepage = "https://xplc.sourceforge.net/"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    # uuid is the hard dependency configure probes for (see module docstring 1).
    # The recipe target is the OHOS triplet profile, so this is unambiguous.
    def requirements(self):
        self.requires("uuid/2.40.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("xplc is supported only on Linux/OHOS")
        if str(self.settings.os) == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # In-tree build: the upstream makefile resolves sources with
        # `wildcard xplc/*.cpp` relative to cwd and has no VPATH support, so a
        # split source/build layout cannot work (acpitool 0.5.1 precedent).
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()

        tc = AutotoolsToolchain(self)
        # 3. PATH here has no /bin, and the bundled 2000-era install-sh cannot
        #    copy several sources into a directory (1/24 headers, rc=0).
        tc.configure_args.append("INSTALL=/bin/install")
        # AutotoolsDeps puts every dependency lib into the LIBS environment
        # variable (conan tools/gnu/autotoolsdeps.py -> env.append("LIBS", libs)),
        # so configure substitutes `LIBS:=-luuid` into config.mk.  This makefile
        # is hand-written and consumes $(LIBS) in *prerequisite* position:
        #     tests/rules.mk:32  tests/testmain: ... libxplc.a libxplc-cxx.a $(LIBS)
        # Make then treats the bare `-luuid` as a file target and aborts with
        #     make: *** No rule to make target '-luuid', needed by 'tests/testmain'.
        # Forcing LIBS empty at configure time reproduces exactly the native
        # state (config.mk `LIBS:=`, because AC_SEARCH_LIBS resolves everything
        # to libc here) while keeping the uuid wiring intact: configure still
        # records `with_uuid:=-luuid` for the uuidgen link, and AutotoolsDeps
        # still supplies `-I<uuid>/include` / `-L<uuid>/lib`.  Verified locally:
        # make + make tests + make install all rc=0, 0 failed / 230 passed,
        # 24 of 24 headers, uuidgen runs.  Doing it here also means every later
        # `make`/`make install` inherits it — the alternative (passing `LIBS=`
        # on each make command line) would have to be repeated per invocation.
        tc.configure_args.append("LIBS=")
        # 2. Keep compiler.cppstd=17; narrowing is fatal there by definition.
        tc.extra_cxxflags.append("-Wno-c++11-narrowing")
        if not self.options.fPIC:
            tc.configure_args.append("--disable-pic")
        tc.generate()

    def _pin_autotools_timestamps(self):
        """boolstuff precedent: after patching, pin the whole autotools chain
        to one historical mtime so make never re-runs autoconf/autoheader and
        rolls the patches back."""
        stamp = time.mktime((2005, 11, 1, 0, 0, 0, 0, 0, -1))
        names = (
            "configure", "configure.ac", "config.guess", "config.sub",
            "install-sh", "config.missing", "config.rpath", "ltmain.sh",
            "aclocal.m4", "Makefile.in", "config.h.in",
        )
        for root, _dirs, files in os.walk(self.source_folder):
            for fname in files:
                if fname in names or fname.endswith((".m4", ".am", ".in", ".ac")):
                    path = os.path.join(root, fname)
                    try:
                        os.utime(path, (stamp, stamp))
                    except OSError:
                        pass  # read-only or vanished helper; not fatal

    def _verify_configure_outputs(self):
        """Ruling ③: `configure` returning 0 does NOT mean it succeeded — the
        HMDFS umask-077 path can make config.status fail to write and leave an
        empty tree while the exit code stays 0."""
        missing = []
        for rel in ("include/autoconf.h", "config/config.mk", "config.status"):
            path = os.path.join(self.source_folder, rel)
            if not (os.path.isfile(path) and os.path.getsize(path) > 0):
                missing.append(rel)
        if missing:
            raise ConanInvalidConfiguration(
                "configure exited 0 but produced no {} — false-green "
                "(autoconf 2.59 + HMDFS umask-077 family); aborting before make"
                .format(", ".join(missing)))

    def _verify_build_outputs(self):
        missing = [rel for rel in ("libxplc.a", "libxplc-cxx.a", "libxplc.so")
                   if not os.path.isfile(os.path.join(self.source_folder, rel))]
        if missing:
            raise ConanInvalidConfiguration(
                "make exited 0 but did not produce {} — false-green"
                .format(", ".join(missing)))

    def _verify_install_outputs(self):
        """Ruling ③ extended to the install stage: the bundled install-sh only
        copies the FIRST source when given many, so `make install` can report
        success while dropping 23 of 24 headers."""
        expected = len(glob.glob(os.path.join(self.source_folder,
                                              "include", "xplc", "*.h")))
        hdr_dir = os.path.join(self.package_folder, "include", "xplc-0.3.13",
                               "xplc")
        installed = len(glob.glob(os.path.join(hdr_dir, "*.h")))
        if expected and installed < expected:
            raise ConanInvalidConfiguration(
                "make install exited 0 but installed {} of {} headers into {} "
                "— false-green (bundled install-sh has no multi-source loop; "
                "INSTALL=/bin/install did not take effect)"
                .format(installed, expected, hdr_dir))
        for rel in ("lib/xplc-0.3.13/libxplc.a",
                    "lib/xplc-0.3.13/libxplc-cxx.a",
                    "lib/libxplc.so.0.3.13",
                    "lib/pkgconfig/xplc-0.3.13.pc",
                    "bin/uuidgen",
                    "bin/uuidcdef"):
            if not os.path.exists(os.path.join(self.package_folder, rel)):
                raise ConanInvalidConfiguration(
                    "make install exited 0 but {} is missing — false-green"
                    .format(rel))

    def _fix_soname(self):
        """minor=3 is odd, so upstream links with
        `SONAME=libxplc.so.0.3.13-unstable` yet installs
        `lib/libxplc.so.0.3.13`.  Consumers therefore die at load time
        (`Error loading shared library libxplc.so.0.3.13-unstable`, verified
        even with LD_LIBRARY_PATH set).  Add the SONAME-named symlink in both
        lib dirs so link-time and run-time resolution agree."""
        real = os.path.join(self.package_folder, "lib", "libxplc.so.0.3.13")
        if not os.path.isfile(real):
            return  # static-only tree, nothing to repair
        wanted = "libxplc.so.0.3.13-unstable"
        for libdir, target in (
            (os.path.join(self.package_folder, "lib"), "libxplc.so.0.3.13"),
            (os.path.join(self.package_folder, "lib", "xplc-0.3.13"),
             os.path.join("..", "libxplc.so.0.3.13")),
        ):
            link = os.path.join(libdir, wanted)
            if os.path.lexists(link):
                os.remove(link)
            if os.path.isdir(libdir):
                os.symlink(target, link)

    def build(self):
        apply_conandata_patches(self)
        self._pin_autotools_timestamps()

        autotools = Autotools(self)
        autotools.configure()
        self._verify_configure_outputs()

        autotools.make(args=["-j1"])
        self._verify_build_outputs()

        # Upstream test entry point is `make tests` (there is no `check`
        # target): 12 registered cases test000..test011, 182 ASSERT/VERIFY in
        # tests/*.cpp + 9 in the shared test.h helpers, 230 assertions
        # executed at runtime.  testmain exits non-zero on any failure.
        autotools.make(target="tests", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()          # DESTDIR=<package_folder> is added by conan
        self._verify_install_outputs()
        self._fix_soname()

    def package_info(self):
        self.cpp_info.libs = ["xplc", "xplc-cxx"]
        self.cpp_info.system_libs = ["dl"]
        # Upstream installs into versioned subdirs (odd minor ⇒ "unstable"):
        #   include/xplc-0.3.13/xplc/*.h  and  lib/xplc-0.3.13/*
        # Consumers write `#include <xplc/core.h>`, so the versioned dir itself
        # must be the include root, and lib/ must follow libdirs because that
        # is where the SONAME symlink lives.
        self.cpp_info.includedirs = ["include/xplc-0.3.13"]
        self.cpp_info.libdirs = ["lib/xplc-0.3.13", "lib"]
        self.cpp_info.bindirs = ["bin"]
        # The library is compiled with -DUNSTABLE but xplc.pc does not carry
        # it; without this the headers fail to compile for every consumer.
        self.cpp_info.defines = ["UNSTABLE"]
        self.cpp_info.set_property("pkg_config_name", "xplc-0.3.13")
        self.runenv_info.prepend_path("PATH",
                                      os.path.join(self.package_folder, "bin"))
        # Runtime library search path for the delivered .so.
        # conan's VirtualRunEnv only calls runenv_from_cpp_info() (the code that
        # prepends LD_LIBRARY_PATH from libdirs) behind `if require.run:`, and
        # require.run is False here because package_type="library" with
        # shared=False (conan internal/model/requires.py: `dep_pkg_type is
        # PackageType.SHARED or require.run`).  The unconditional branch is
        # `dep.runenv_info`, which is what this recipe already uses for PATH —
        # so declare the lib dirs there too.  Without it a consumer that links
        # the delivered libxplc.so dies at load time with
        #     Error loading shared library libxplc.so.0.3.13-unstable
        # even though the SONAME symlink installed by package() is correct.
        # Both dirs are listed to mirror cpp_info.libdirs (lib/ holds the real
        # .so + SONAME link, lib/xplc-0.3.13/ holds the dev link).
        for _libdir in ("lib", os.path.join("lib", "xplc-0.3.13")):
            self.runenv_info.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.package_folder, _libdir))
