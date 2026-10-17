#!/usr/bin/env python3
"""Conan recipe — libf2c2 20240504 (upstream makefile.u, raw C sources).

libf2c2 is the Fortran run-time library of f2c.  f2c translates Fortran to C
and leaves the intrinsic functions, the character-string helpers and the whole
formatted / list-directed I/O run time to this library, so f2c output is
normally compiled and linked with -lf2c.  netlib publishes it as a flat
`libf2c.zip` of 184 files — 160 C sources plus header files and upstream's
own `makefile.u` — and there is no
configure/CMake/meson layer and no release archive with a version in its name.

Version provenance
------------------
netlib does not version the archive, so the label 20240504 is the upstream
snapshot date under which Debian ships exactly this library (source package
`libf2c2` 20240504-1, whose Homepage is https://netlib.org/f2c/ and whose
orig tarball is this zip repacked).  The zip pinned in conandata.yml is
byte-for-byte the 184 files of `libf2c2_20240504.orig.tar.xz`, so the version
label and the artifact agree — the comparison is recorded in notes.md.

OHOS adaptation
---------------
Two patches, neither of them an OHOS-specific branch; both are upstream
portability defects that the OHOS toolchain merely makes visible:

* patches/0001 — uninit.c implements f2c's -trapuv support and, under
  `#ifdef __linux__`, includes "fpu_control.h" to unmask the FP exceptions
  that make uninitialised variables fatal.  `fpu_control.h` is a glibc
  header; the OHOS sysroot is musl-based and does not ship it, and the OHOS
  clang driver still defines `__linux__`, so the build stopped at
  `uninit.c:236: fatal error: 'fpu_control.h' file not found`.  The guard,
  not the platform, was wrong: the patch narrows it to
  `defined(__linux__) && defined(__GLIBC__)`.  On glibc nothing changes; on
  musl the build now reaches upstream's own `ieee0() {}` fallback, the one
  upstream already provides for every non-Linux target.  Only -trapuv's
  FP-exception unmasking is unavailable there, exactly as it already is on
  every non-glibc system, and `_uninit_f2c` keeps working (test_package
  checks that it still fills uninitialised REAL and DOUBLE PRECISION values
  with NaN, which is what -trapuv detects).  No `__OHOS__` macro is
  introduced.

* patches/0002 — upstream puts main.c into the library, so a program that
  links -lf2c for its run time inherits f2c's entry point, and main.c leaves
  `MAIN__` undefined because the translated program supplies it.  In a
  shared library that dangling reference is fatal: lld (and current
  binutils) default to --no-allow-shlib-undefined and refuse to link an
  executable against a .so with undefined symbols —
  `ld.lld: error: undefined reference due to --no-allow-shlib-undefined:
  MAIN__`.  The patch gives main() and MAIN__ weak definitions, so a
  translated program's strong MAIN__ (and any C program's own main) still
  wins while the library itself is self-contained.  This is the same defect
  Debian tracks as #826253; test_package links both a plain consumer and a
  translated-program-style consumer that defines MAIN__ and takes its entry
  point from the library.

The build itself follows Debian's reference invocation of upstream's own
makefile: `make -f makefile.u` with -fPIC, -DNON_UNIX_STDIO (upstream's
makefile header prescribes it for Linux).  The default flag/ftnlen/ftnint ABI
needs no define: f2c.h has a single `#ifdef f2c_i2` branch and nothing in the
sources consumes a bare `f2c` macro, so the default ABI is the one you get by
not passing -Df2c_i2.  f2c.h is generated the way the
upstream README prescribes for a target where sizeof(long) == 8 — "removing
the first occurrence of 'long ' on each line containing 'long '", i.e.
`sed 's/long int /int /' f2c.h0 > f2c.h` — which is what makes the on-target
`integer` an int (4 bytes) rather than a long (8 bytes).  signal1.h,
sysdep1.h and fio.h come from the .h0 files as makefile.u's own rules do, and
arith.h is produced by compiling and running upstream's arithchk.c, which
works here because the profile builds for and on OHOS/aarch64.

Scope note on libf2c_i2: Debian's binary package also ships libf2c_i2.so.2,
the run time for code generated with `f2c -i2` (only flag/ftnlen/ftnint
become short, selected by -Df2c_i2).  This recipe builds the default ABI
only: the f2c compiler is not packaged in this repository, so nothing in the
ecosystem can generate -i2 code, and both ABIs export the same symbol names,
so they can never share a link line.  notes.md records the exact command if
that variant is ever needed.

Upstream test situation: libf2c.zip ships no test program.  Its makefile has
a `check` target, but that only compares source checksums against xsum0.out
and needs the `xsum` tool, which is distributed with the separate f2c
compiler source and is not part of this archive.  Verification therefore
rests on test_package/, which drives the installed library through its real
ABI.  See notes.md.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

# Shared-library names of the reference packaging: the on-disk file keeps the
# full version, the SONAME keeps the upstream ABI version 2.
SHARED_REAL_NAME = "libf2c.so.2.1"
SHARED_SONAME = "libf2c.so.2"


class Libf2c2Conan(ConanFile):
    name = "libf2c2"
    version = "20240504"
    description = "Fortran run-time library for C code generated by f2c"
    license = "AT&T"
    homepage = "https://netlib.org/f2c/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }
    exports_sources = "conandata.yml", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # The run time is plain C; dropping the C++ settings keeps consumers
        # from inheriting a libstdc++/libc++ split this library never uses.
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        basic_layout(self)
        # makefile.u is written for an in-source build (it compiles $*.c from
        # the current directory and writes arith.h there), so the build folder
        # is the source folder.
        self.folders.build = "."

    def source(self):
        # libf2c.zip has no leading directory: the 184 files land directly in
        # the source folder, so there is nothing to strip.
        get(self, **self.conan_data["sources"])

    def validate(self):
        # The run time is POSIX C: it needs unistd.h, stdio.h and the Fortran
        # unit files, so Windows is out of scope.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} is the f2c run time for POSIX targets, "
                f"{self.settings.os} is not supported"
            )

    def _generate_headers(self):
        """Produce the derived headers exactly as upstream's makefile does.

        f2c.h is the one that is not a plain copy: upstream's README says
        that on machines where sizeof(long) == 8 (this target), f2c.h must be
        obtained with `sed 's/long int /int /' f2c.h0 > f2c.h` so that
        Fortran INTEGER maps to a 4-byte int.  Doing it here rather than
        through makefile.u's `f2c.h: f2c.h0` copy rule also keeps make from
        overwriting the adjusted header, which the makefile never
        regenerates once it is newer than f2c.h0.
        """
        source_folder = self.source_folder
        with open(os.path.join(source_folder, "f2c.h0"), encoding="utf-8") as handle:
            header = handle.read()
        adjusted = header.replace("long int ", "int ")
        if adjusted == header:
            # f2c.h0 changed upstream: stop instead of silently shipping the
            # 8-byte INTEGER ABI.
            raise ConanInvalidConfiguration(
                "f2c.h0 has no 'long int' typedefs left; the LP64 adjustment "
                "prescribed by the upstream README no longer applies"
            )
        with open(os.path.join(source_folder, "f2c.h"), "w", encoding="utf-8") as handle:
            handle.write(adjusted)
        for name in ("signal1.h", "sysdep1.h", "fio.h"):
            shutil.copyfile(
                os.path.join(source_folder, name + "0"),
                os.path.join(source_folder, name),
            )

    def build(self):
        apply_conandata_patches(self)
        self._generate_headers()

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        jobs = self.conf.get("tools.build:jobs", default=1, check_type=int)

        cflags = ["-O2" if str(self.settings.build_type) == "Release" else "-O0"]
        if self.options.get_safe("fPIC") or self.options.shared:
            cflags.append("-fPIC")
        cflags.extend(self.conf.get("tools.build:cflags", default=[], check_type=list))
        # -DNON_UNIX_STDIO is what upstream's makefile header prescribes for
        # Linux targets (binary-mode I/O on the unit files).  No ABI define
        # is needed for the default flag/ftnlen/ftnint types: f2c.h branches
        # on `#ifdef f2c_i2`, which is exactly the -i2 variant this recipe
        # does not build.
        cflags.append("-DNON_UNIX_STDIO")
        cflags.extend(self.conf.get("tools.build:defines", default=[], check_type=list))

        self.run(
            'make -f makefile.u -j{} CC="{}" CFLAGS="{}" libf2c.a'.format(
                jobs, cc, " ".join(cflags)
            ),
            cwd=self.source_folder,
        )

        if self.options.shared:
            objects = sorted(
                name
                for name in os.listdir(self.source_folder)
                if name.endswith(".o")
            )
            if not objects:
                raise ConanInvalidConfiguration(
                    "makefile.u produced no objects; refusing to link an empty library"
                )
            # Link the shared object the way the reference packaging does, so
            # the ABI keeps its upstream name and version.
            self.run(
                '{} -shared -Wl,-soname,{} -o {} {} -lm'.format(
                    cc, SHARED_SONAME, SHARED_REAL_NAME, " ".join(objects)
                ),
                cwd=self.source_folder,
            )

    def package(self):
        copy(
            self,
            "Notice",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "f2c.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
            keep_path=False,
        )
        libdir = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            os.makedirs(libdir, exist_ok=True)
            copy(
                self,
                SHARED_REAL_NAME,
                src=self.source_folder,
                dst=libdir,
                keep_path=False,
            )
            # libf2c.so.2 is the SONAME consumers record; libf2c.so is what
            # -lf2c resolves at link time.
            for link, target in (
                (SHARED_SONAME, SHARED_REAL_NAME),
                ("libf2c.so", SHARED_SONAME),
            ):
                os.symlink(target, os.path.join(libdir, link))
        else:
            copy(
                self,
                "libf2c.a",
                src=self.source_folder,
                dst=libdir,
                keep_path=False,
            )

    def package_info(self):
        self.cpp_info.libs = ["f2c"]
        # The run time calls libc's math functions (erf/erfc/pow/log10/...);
        # on HarmonyOS those resolve through libc, and -lm keeps the static
        # archive linkable elsewhere.
        self.cpp_info.system_libs = ["m"]
