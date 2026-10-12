#!/usr/bin/env python3
"""pd-zexy 2.4.4 — zexy, the Swiss army knife of Pure Data externals.

zexy builds a single `zexy.pd_linux` holding ~90 classes with pd-lib-builder
(vendored in-tree as `pd-lib-builder/Makefile.pdlibbuilder`).  On OHOS two
things are required on top of the plain `make`:

  * the compiler must be injected explicitly and `PDINCLUDEDIR` must point at
    the `puredata` package's `include/pd`: the machine ships neither `cc` nor
    `gcc`, so pd-lib-builder's `cc -dumpmachine` triplet probe hard-fails before
    compiling anything.  (Same treatment as pd-vbap.)
  * `with-lpt=no` must be passed.  zexy probes `<sys/io.h>` through `$(CPP)` and
    the OHOS sysroot *does* ship that header, but musl has no `ioperm`/`inb`/
    `outb`.  The probe therefore reports success, the x86 parallel-port object
    gets compiled in, and its unresolved symbols make the *entire*
    `zexy.pd_linux` fail to relocate at `dlopen()` time.  Measured with the
    upstream regression suite: 13 PASS / 19 FAIL without the flag, 32 PASS /
    0 FAIL / 4 XFAIL with it.

Reusable knowledge entry for this class of problem: `skills/pd-externals-ohos/`
(shipped with the pd-vbap PR #14210, still open against main).
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PdZexyConan(ConanFile):
    name = "pd-zexy"
    version = "2.4.4"
    description = "zexy — Pure Data externals collection (list/symbol/message and DSP classes)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/iem-projects/pd-zexy"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # The artefacts are runtime plugins dlopen()ed by the Pd host; conan's
    # package_type "library" would demand a declarable `shared` option, which
    # makes no sense here (a static Pd external does not exist).
    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Header source only: Pd's internal headers (m_pd.h, s_stuff.h, ...) live
        # in include/pd of the puredata package; libpd ships include/libpd and no
        # internal headers, so it cannot be used to compile externals.
        self.requires("puredata/0.54.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        # conan_data["sources"] is keyed by version; filename= is required because
        # the Debian orig tarball name does not end in the version key and conan
        # otherwise cannot tell which unpacker to use (.tar.xz).
        get(self, **self.conan_data["sources"][self.version], strip_root=True,
            filename="pd-zexy_2.4.4.orig.tar.xz")

    def build(self):
        apply_conandata_patches(self)
        # R32/R33: take the compiler from the Conan toolchain/profile conf, not
        # from an ambient ${CC} (absent in CI, present in some dev sessions).
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict)
        cc = compilers.get("c") or "clang"
        pd_include = os.path.join(self.dependencies["puredata"].package_folder,
                                  "include", "pd")
        # with-lpt=no: disable the x86 parallel-port object (see the module
        # docstring for the measurement).  -j1 per E525.
        self.run('make -j1 CC="{}" PDINCLUDEDIR="{}" with-lpt=no'.format(cc, pd_include),
                 cwd=self.source_folder)

    def package(self):
        copy(self, "LICENSE.txt",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*.pd_linux",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib", "pd-externals"))
        # Pd host resources: root-level abstractions/aliases (zexy-meta.pd, mux.pd,
        # l2s.pd, ...), the abs/ and reference/ help patches and the upstream
        # regression suite under tests/ (including its testrunner.sh driver).
        copy(self, "*.pd",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "pd-zexy"))
        # abs/, reference/ and tests/ are copied verbatim (not only *.pd): the
        # upstream regression suite needs its non-.pd data (tests/msgfile/*.txt
        # reference files, runtests.sh/bat, README.txt) and the help patches ship
        # their own documentation files.
        for sub in ("abs", "reference", "tests"):
            copy(self, "*",
                 src=os.path.join(self.source_folder, sub),
                 dst=os.path.join(self.package_folder, "share", "pd-zexy", sub))
        # Documentation files (explicit list: a "*.txt" glob also sweeps conan's
        # own conaninfo.txt into the package).
        for doc in ("README.txt", "ChangeLog", "LICENSE.txt"):
            copy(self, doc,
                 src=self.source_folder,
                 dst=os.path.join(self.package_folder, "share", "pd-zexy"))

    def package_info(self):
        # The .pd_linux files are runtime plugins dlopen()ed by the Pd host, not
        # linkable libraries: exposing them through cpp_info.libs would make a
        # consumer emit -lzexy and fail at link time.
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/pd-externals"]
        self.cpp_info.resdirs = ["share/pd-zexy"]
