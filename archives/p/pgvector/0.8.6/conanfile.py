#!/usr/bin/env python3
"""Conan recipe for pgvector 0.8.6 (OHOS PC aarch64 adaptation).

pgvector is the PostgreSQL extension providing the ``vector``, ``halfvec``,
``sparsevec`` and ``bit`` types plus the ``ivfflat`` and ``hnsw`` approximate
nearest-neighbour index access methods.

Build system: PGXS (PostgreSQL Extension Building Infrastructure).  The
upstream Makefile does ``PGXS := $(shell $(PG_CONFIG) --pgxs)`` /
``include $(PGXS)`` and every translation unit hard-includes PostgreSQL
*server* headers (postgres.h, fmgr.h, utils/array.h, ...).  A plain libpq
client install is not enough — the full server development tree
(``pg_config`` + PGXS makefiles + ``include/server``) is required.

postgresql/18.3 is published in the ohpcd registry as a complete server +
client package (pg_config, PGXS, server headers, postgres/initdb/pg_ctl/
createdb/psql), so it is declared as a ``tool_requires`` instead of vendoring
the PostgreSQL source tree: no upstream PostgreSQL source is duplicated into
this archive and no third-party patch is carried here.  The same package is
reused by test_package to drive the upstream SQL regression suite against a
real server.

Design notes:
  R26: the package ships the loadable module ``vector.so`` only — no system
       library has that basename, so no static-link requirement applies.
  R32: the platform check accepts both Linux and OHOS.
  R33: no raw shell variables are used in self.run(); the compiler comes from
       PGXS' own ``pg_config --cc``.
  R34: test_package really loads the extension into a running PostgreSQL and
       executes SQL against it (plus the upstream pg_regress suite).
  R39: conandata.yml points at the official upstream GitHub tag archive.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PgvectorConan(ConanFile):
    name = "pgvector"
    version = "0.8.6"
    description = (
        "PostgreSQL extension for vector similarity search: vector/ halfvec/"
        " sparsevec/bit types and the ivfflat + hnsw index access methods"
    )
    license = "PostgreSQL"
    homepage = "https://github.com/pgvector/pgvector"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # The deliverable is a PostgreSQL loadable module (dlopen'ed by the server
    # at CREATE EXTENSION time), not a link library.
    package_type = "library"
    # Conan requires the ``shared`` option for package_type="library".  The
    # module is always built shared (upstream produces a single vector.so
    # loadable module), so the option is declarative only.
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    settings = "os", "arch", "compiler", "build_type"

    # Upstream regression assets vendored into the package for the consumer
    # harness (test_package): 14 pg_regress groups (test/sql + test/expected).
    _UPSTREAM_TEST_DIRS = ("test/sql", "test/expected")

    def configure(self):
        # The OHOS profile declares settings.os.version=6.0, but neither the
        # build nor the package_id depends on it.  Drop it so the package is
        # not held invalid by an undeclared setting value (same pattern as
        # archives/p/postgresql/16.10).
        self.settings.rm_safe("os.version")

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # pg_config + PGXS + include/server + (for test_package) a full server.
        # Published in the ohpcd registry — see notes.md.
        self.tool_requires("postgresql/18.3")

    def validate(self):
        # R32: the platform guard must accept Linux and OHOS alike
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pgvector is only supported on Linux/OHOS, not "
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
            "pg_config not found — postgresql/18.3 tool_requires did not "
            "contribute its bin/ directory"
        )

    def build(self):
        pg_config = self._pg_config()

        # Extra make variables (all three are upstream/PGXS documented):
        #   OPTFLAGS=      upstream README: "To compile for portability, run:
        #                  make OPTFLAGS=''" — drops -march=native.  The
        #                  artifact is published for every OHOS PC aarch64
        #                  device, so it must not be tuned to the CPU of the
        #                  build machine.
        #   enable_rpath=  PGXS would otherwise bake the *build machine's*
        #                  <postgresql package>/lib into the module RUNPATH
        #                  (Makefile.global: LDFLAGS += $(rpath),
        #                  rpathdir = $(libdir)).  The module itself only
        #                  needs libc, so the RUNPATH is dropped to keep the
        #                  artifact relocatable.  Verified: readelf -d shows
        #                  NEEDED libc.so and no RUNPATH.
        #   -j            19 small translation units; no ordering constraint.
        jobs = max(1, os.cpu_count() or 1)
        self.run(
            f'make PG_CONFIG="{pg_config}" OPTFLAGS= enable_rpath= -j{jobs}',
            cwd=self.source_folder,
        )

    def package(self):
        # Loadable module
        copy(
            self,
            "vector.so",
            self.source_folder,
            os.path.join(self.package_folder, "lib"),
        )
        # Extension control file + version SQL scripts (the 0.8.6 install
        # script is generated by the upstream Makefile from sql/vector.sql,
        # the remaining members are the incremental upgrade scripts).
        copy(
            self,
            "vector.control",
            self.source_folder,
            os.path.join(self.package_folder, "extension"),
        )
        copy(
            self,
            "vector--*.sql",
            os.path.join(self.source_folder, "sql"),
            os.path.join(self.package_folder, "extension"),
        )
        # Vendor the upstream regression assets so test_package can execute
        # the unmodified upstream suite against a live server.
        for rel in self._UPSTREAM_TEST_DIRS:
            copy(
                self,
                "*",
                os.path.join(self.source_folder, rel),
                os.path.join(self.package_folder, "upstream", rel),
            )
        copy(
            self,
            "LICENSE",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # vector.so is a PostgreSQL loadable module (dlopen'ed by the server
        # through $libdir/vector), not a link library — it carries no SONAME
        # and leaves the PostgreSQL server symbols undefined on purpose.  The
        # cpp_info entry follows the convention of the other PostgreSQL
        # extension recipes in this repository; the real consumer interface is
        # "copy lib/vector.so into $(pg_config --pkglibdir) and
        # extension/* into $(pg_config --sharedir)/extension".
        self.cpp_info.libs = ["vector"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.resdirs = ["extension"]
