#!/usr/bin/env python3
"""Conan recipe for pgcopydb 0.18 on HarmonyOS.

pgcopydb is a PostgreSQL logical/physical data copy tool. It builds with the
upstream hand-written Makefile, which is entirely driven by the `pg_config`
binary (--cc, --includedir, --includedir-server, --pkgincludedir/internal,
--libdir, --pkglibdir, --libs).

Upstream links against the Postgres client library plus a few PostgreSQL
frontend helpers (`-lpq -lpgcommon -lpgport`) and the Boehm-Demers-Weiser
conservative garbage collector (`-lgc`, whose malloc/free/strdup are #define'd
over the whole program in src/bin/pgcopydb/defaults.h).  Both are published on
the ohpcd registry: `postgresql/18.3` ships the complete server + client
install (pg_config, libpq, libpgcommon, libpgport, server headers, pg_dump,
pg_restore) and `gc/8.2.12` ships `gc/gc.h` + libgc.a.

OHOS adaptation (see notes.md): the platform sandbox rejects every System V IPC
syscall (semget/msgget/shmget raise SIGSYS, so the process dies with "Bad
system call" before printing anything), and musl's getopt_long() ignores
POSIXLY_CORRECT, which breaks the sub-command dispatching.  Both are addressed
by patches/0001-ohos-platform-adaptation.patch, whose OHOS-only branches are
selected by semantic capability macros defined from `build()` below (R8: no
platform macro in patches/).
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


class PgcopydbConan(ConanFile):
    name = "pgcopydb"
    version = "0.18"
    description = ("Command line tool to copy a full Postgres database to "
                   "another Postgres database")
    license = "PostgreSQL"
    homepage = "https://github.com/dimitri/pgcopydb"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Full server + client install: this is the only published package
        # that provides pg_config together with the *server* headers that
        # pgcopydb includes (postgres.h, postgres_fe.h, access/xlogdefs.h,
        # common/pg_prng.h, port/pg_bswap.h, ...) and the libpgcommon /
        # libpgport frontend helpers it links against.  Its pg_dump and
        # pg_restore are also what pgcopydb shells out to at run time.
        self.requires("postgresql/18.3")
        # Boehm-Demers-Weiser GC: malloc/calloc/free/realloc/strdup/strndup
        # are #define'd over the whole program (src/bin/pgcopydb/defaults.h)
        # and main() installs GC_malloc/GC_free as parson's allocators.
        self.requires("gc/8.2.12")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pgcopydb recipe supports Linux and OHOS, not {self.settings.os}"
            )
        if str(self.settings.arch) not in ("armv8", "aarch64", "x86_64"):
            raise ConanInvalidConfiguration(
                f"pgcopydb recipe has not been verified for {self.settings.arch}"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        pg_folder = self.dependencies["postgresql"].package_folder
        gc_folder = self.dependencies["gc"].package_folder
        pg_config = os.path.join(pg_folder, "bin", "pg_config")
        pg_libdir = os.path.join(pg_folder, "lib")
        gc_libdir = os.path.join(gc_folder, "lib")

        # R33: take the compiler from Conan, never from the shell environment.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")

        cflags = [f"-I{os.path.join(gc_folder, 'include')}"]

        # Link against the packaged dependencies and record them as RUNPATH so
        # that the binary finds libpq.so.5 without LD_LIBRARY_PATH.  libpq is
        # taken as a shared library on purpose: the static libpq.a shipped by
        # the postgresql package is incomplete (it refers pg_encoding_to_char,
        # which the frontend libpgcommon provides only under the *shared*
        # variant used by the server).
        ldflags = [
            f"-L{pg_libdir}",
            f"-Wl,-rpath,{pg_libdir}",
            f"-L{gc_libdir}",
            f"-Wl,-rpath,{gc_libdir}",
        ]

        # Upstream links -lncurses unconditionally although no ncurses symbol
        # is used anywhere in the sources (the only hits are inside the
        # vendored sqlite3.c amalgamation), so it is dropped here rather than
        # pulling a useless runtime dependency.
        libs = ["-lpq", "-lpgcommon", "-lpgport", "-lgc", "-lm"]

        if str(self.settings.os) == "OHOS":
            # R8 (iron-rules): patches/ must stay free of platform macros
            # (#ifdef __OHOS__); the platform decision lives here, in the
            # recipe, and the patch hunks are guarded by semantic capability
            # macros.  On other platforms the guarded code compiles out.
            cflags.extend([
                # semget()/semctl()/semop() raise SIGSYS (unimplemented)
                "-DHAVE_BROKEN_SYSV_SEM",
                # msgget()/msgsnd()/msgrcv()/msgctl() raise SIGSYS too
                "-DHAVE_BROKEN_SYSV_MSG",
            ])

        # The Makefile runs GIT-VERSION-GEN (whose shebang is #!/bin/sh) to
        # produce GIT-VERSION-FILE.  GIT-VERSION-FILE has no prerequisite, so
        # providing it up-front both pins the version that the upstream
        # release tarball was cut from and keeps the build independent from
        # the availability of a POSIX shell.
        save(self, os.path.join(self.source_folder, "GIT-VERSION-FILE"),
             f"GIT_VERSION = {self.version}\n")
        save(self, os.path.join(self.source_folder, "version"),
             f"{self.version}\n")

        make_args = [
            "bin",
            "-j1",
            f"PG_CONFIG={pg_config}",
            f"CC={cc}",
            f'CFLAGS="{" ".join(cflags)}"',
            f'LDFLAGS="{" ".join(ldflags)}"',
            f'LIBS="{" ".join(libs)}"',
        ]

        # The upstream Makefile only supports in-tree builds, so point make at
        # the source folder explicitly (-C); Conan runs commands from the
        # build folder otherwise.
        self.run("make -C " + shlex.quote(self.source_folder) + " "
                 + " ".join(make_args))

    def package(self):
        copy(self,
             "pgcopydb",
             src=os.path.join(self.source_folder, "src", "bin", "pgcopydb"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self,
             "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

        binary = os.path.join(self.package_folder, "bin", "pgcopydb")
        if os.path.isfile(binary):
            os.chmod(binary, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
