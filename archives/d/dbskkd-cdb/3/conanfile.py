#!/usr/bin/env python3
"""Conan recipe — dbskkd-cdb 3.00 (plain Makefile + static libcdb.a)

dbskkd-cdb is the dictionary server of the SKK Japanese input method system.
It speaks the SKK server protocol on stdin/stdout (the inetd model) and
answers every conversion request from a cdb constant database converted from
an SKK-JISYO dictionary.

Version slug
------------
The task card and archive directory version is the single character "3",
which Conan rejects before any build starts: ConanName requires at least two
characters (conan/api/model/refs.py:

    validation_pattern = re.compile(r"^[a-z0-9_][a-z0-9_+.-]{1,100}\\Z")

so `conan create` aborts with "Invalid package version '3'"). set_version()
therefore normalizes the artifact version to the upstream release identifier
`3.00` (git tag `3.00`, CHANGES.md "Version 3.00", and the VERSION string
"dbskkd-cdb-3.00 " compiled into the program). The archive directory and the
branch keep the task card value because the CI L0n gate requires the branch
name to be exactly <package>-<archive version>.

Build system
------------
Upstream ships a plain Makefile with three properties that make a faithful
build without a Makefile patch impossible to drive by the Conan toolchain:
the compiler and its flags are a single value (`CC = cc -Wall -O2 -g
-I/usr/local/include`), the cdb library is a hardcoded static archive path
(`CDBLIB = /usr/local/lib/libcdb.a`) and `install` copies the binary to
/usr/local/libexec. Passing CC/COMPAT/CDBLIB on the make command line
replaces all three (and drops the /usr/local include path), so no Makefile
patch is needed; the binary is installed by package() itself.

Dictionary location
-------------------
JISYO_FILE defaults to /usr/local/share/skk/SKK-JISYO.L.cdb, a path that can
neither be created nor written on an OHOS device, and the upstream build
offers no way to point the program somewhere else. Patch 0001 adds a runtime
override (argv[1], then the DBSKKD_JISYO environment variable, then the
unchanged compiled-in default) with no platform conditional and no change to
the protocol or the default behaviour.
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class DbskkdCdbConan(ConanFile):
    name = "dbskkd-cdb"
    description = "SKK dictionary server based on cdb constant databases (DJB cdb / TinyCDB compatible)"
    license = "MIT"
    homepage = "https://github.com/jj1bdx/dbskkd-cdb"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def set_version(self):
        # Artifact version normalization, see the module docstring: the archive
        # directory keeps the task card value "3" for the CI branch gate, the
        # artifact itself uses the upstream release identifier.
        self.version = "3.00"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # cdb.h + libcdb.a (the tinycdb-compatible API the program uses). The
        # build links the static archive like the upstream Makefile does, so
        # the packaged binary has no runtime dependency on the cdb package.
        self.requires("cdb/20251021")

    def layout(self):
        basic_layout(self)

    # R32: POSIX C program over the cdb library, Linux and OHOS only.
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} only supports Linux and OHOS, not {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler and flags come from the Conan profile/toolchain, never
        # from a bare ${CC}/${CFLAGS} in the shell environment.
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_executables.get("c") or "clang"
        tc = GnuToolchain(self)
        # GnuToolchain.defines yields bare macro names (no "-D" prefix), the
        # Autotools/CMake helpers add the prefix themselves — do the same here.
        cflags = " ".join(tc.cflags + [f"-D{define}" for define in tc.defines])

        cdb_info = self.dependencies["cdb"].cpp_info
        includes = " ".join(f"-I{inc}" for inc in cdb_info.includedirs)
        libdirs = cdb_info.libdirs or [
            os.path.join(self.dependencies["cdb"].package_folder, "lib")
        ]
        # Upstream links the static archive explicitly (CDBLIB); keep that and
        # fail loudly rather than silently falling back to a system libcdb.
        archive = None
        for lib in cdb_info.libs or ["cdb"]:
            candidate = os.path.join(libdirs[0], f"lib{lib}.a")
            if os.path.isfile(candidate):
                archive = candidate
                break
        if archive is None:
            raise ConanException(
                f"cdb static archive lib*.a not found in {libdirs[0]} — "
                f"the cdb package must provide the static library"
            )

        # R9: a one-object project, keep the build single job. The Makefile's
        # own PRIVATE/COMPAT hooks carry the profile flags and the cdb include
        # path; CC and CDBLIB are replaced wholesale.
        self.run(
            f'make -j1 CC="{cc}" COMPAT="{cflags} {includes}" CDBLIB="{archive}"',
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "dbskkd-cdb", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Command-line server tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
