#!/usr/bin/env python3
"""Conan recipe for pg_crash 0.3 (OHOS PC aarch64 adaptation).

pg_crash is a PostgreSQL extension that periodically or randomly crashes
the database infrastructure (kill/postmaster-reset signals) — it is an
HA/failover testing tool, not a normal "crash fixer".

Build system: PGXS (PostgreSQL Extension Building Infrastructure).  The
upstream Makefile does ``PGXS := $(shell $(PG_CONFIG) --pgxs)`` /
``include $(PGXS)`` and the single translation unit hard-includes
PostgreSQL *server* headers (c.h, postgres.h, fmgr.h, miscadmin.h,
postmaster/bgworker.h, storage/proc.h, utils/guc.h).  A plain libpq
client install is not enough — the full server development tree
(``pg_config`` + PGXS makefiles + server headers) is required.

postgresql/16.10 is published in the ohpcd registry as a complete
server + client package (pg_config, PGXS, server headers, initdb/
postgres/pg_ctl/psql), so it is declared as a ``tool_requires`` instead
of vendoring the PostgreSQL source tree: no upstream PostgreSQL source
is duplicated into this archive and no third-party patch is carried.

Design notes:
  R26: the package ships the loadable module ``pg_crash.so`` only — no
       system library has that basename, so no static-link requirement
       applies.
  R32: the platform check accepts both Linux and OHOS.
  R33: no raw shell variables are used in self.run(); the compiler comes
       from PGXS' own ``pg_config --cc`` (the clang used to build the
       postgresql package itself, same OHOS SDK toolchain).
  R34: test_package dlopen()s the module on the OHOS device, verifies
       the PostgreSQL magic block and the _PG_init symbol, then drives a
       real postgres instance end-to-end (CREATE EXTENSION + worker GUCs).
  R39: conandata.yml points at the official upstream GitHub tag archive.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PgCrashConan(ConanFile):
    name = "pg-crash"
    version = "0.3"
    description = (
        "PostgreSQL extension to periodically or randomly crash the "
        "database infrastructure (HA / failover testing)"
    )
    license = "BSD-3-Clause"
    homepage = "https://github.com/cybertec-postgresql/pg_crash"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # The deliverable is a PostgreSQL loadable module (dlopen'ed by the
    # server at CREATE EXTENSION time), not a link library.
    package_type = "library"
    # Conan requires the ``shared`` option for package_type="library".  The
    # module is always built shared (upstream produces a single pg_crash.so
    # loadable module), so the option is declarative only.
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    settings = "os", "arch", "compiler", "build_type"

    def configure(self):
        # The OHOS profile declares settings.os.version=6.0, but neither the
        # build nor the package_id depends on it.  Drop it so the package is
        # not held invalid by an undeclared setting value (same pattern as
        # archives/p/postgresql/16.10 and archives/p/pgvector/0.8.6).
        self.settings.rm_safe("os.version")

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # pg_config + PGXS + server headers + (for test_package) a full server.
        # Published in the ohpcd registry — see notes.md.
        self.tool_requires("postgresql/16.10")

    def validate(self):
        # R32: the platform guard must accept Linux and OHOS alike
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pg_crash is only supported on Linux/OHOS, not "
                f"{self.settings.os}"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _pg_config(self):
        """Absolute path of the pg_config provided by tool_requires."""
        dep = self.dependencies.build["postgresql"]
        for bindir in dep.cpp_info.bindirs:
            candidate = os.path.join(bindir, "pg_config")
            if os.path.isfile(candidate):
                return candidate
        found = shutil.which("pg_config")
        if found:
            return found
        raise ConanException(
            "pg_config not found — postgresql/16.10 tool_requires did not "
            "contribute its bin/ directory"
        )

    def build(self):
        pg_config = self._pg_config()

        # Extra make variables (PGXS-documented):
        #   enable_rpath=  PGXS would otherwise bake the *build machine's*
        #                  <postgresql package>/lib into the module RUNPATH
        #                  (Makefile.global: LDFLAGS += $(rpath)).  The
        #                  module itself only needs libc, so the RUNPATH is
        #                  dropped to keep the artifact relocatable.
        #   -j             1 translation unit; -j is harmless but omitted
        #                  for a deterministic single-file build.
        self.run(
            f'make PG_CONFIG="{pg_config}" enable_rpath=',
            cwd=self.source_folder,
        )

    def package(self):
        # Loadable module
        copy(
            self,
            "pg_crash.so",
            self.source_folder,
            os.path.join(self.package_folder, "lib"),
        )
        # NOTE: upstream Makefile has no EXTENSION/DATA rule — it builds only
        # the loadable module (MODULE_big).  There is no pg_crash.control /
        # pg_crash--0.3.sql in the tarball (Debian ships its own packaging).
        # The module registers its GUCs in _PG_init() and is loaded via
        # shared_preload_libraries, so no control/SQL file is required.
        copy(
            self,
            "LICENSE",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # pg_crash.so is a PostgreSQL loadable module (dlopen'ed by the
        # server through $libdir/pg_crash), not a link library — it carries
        # no SONAME and leaves the PostgreSQL server symbols undefined on
        # purpose.  The real consumer interface is "copy lib/pg_crash.so
        # into $(pg_config --pkglibdir) and extension/* into
        # $(pg_config --sharedir)/extension".
        self.cpp_info.libs = ["pg_crash"]
        self.cpp_info.libdirs = ["lib"]
