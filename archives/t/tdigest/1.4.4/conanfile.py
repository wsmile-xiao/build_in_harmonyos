#!/usr/bin/env python3
"""Conan recipe — tdigest 1.4.4 (PostgreSQL server extension).

tdigest implements the t-digest data structure as PostgreSQL aggregates:
``tdigest_percentile`` / ``tdigest_digest`` / ``tdigest``, for on-line
accumulation of rank-based statistics (quantiles, trimmed means) and for
merging partial digests produced by parallel workers.

The build artifact is a PostgreSQL *server-side* extension module
(``tdigest.so``) that a running postgres process dlopens at
``CREATE EXTENSION`` time, plus ``tdigest.control`` and the
``tdigest--*.sql`` install/upgrade scripts.

Build strategy: the upstream Makefile is a standard PGXS extension makefile
(``PG_CONFIG = pg_config`` / ``PGXS := $(shell $(PG_CONFIG) --pgxs)`` /
``include $(PGXS)``) and ``tdigest.c`` hard-includes PostgreSQL *server*
headers (``postgres.h``, ``libpq/pqformat.h``, ``utils/array.h``,
``utils/builtins.h``, ``utils/lsyscache.h``, ``catalog/pg_type.h``). Server
headers, the PGXS makefile infrastructure, a relocatable ``pg_config`` and a
runnable server (initdb/postgres/pg_ctl/pg_regress, used by test_package) all
come from the conan ``postgresql`` package — no PostgreSQL source build and no
source patch is needed on OHOS.

Verified on OHOS PC (aarch64, clang 15.0.4 + OHOS musl toolchain):
``make`` completes with zero warnings/errors and the upstream regression suite
(10 test groups, driven by pg_regress) passes 10/10 — see notes.md.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class TdigestConan(ConanFile):
    name = "tdigest"
    version = "1.4.4"
    description = (
        "PostgreSQL extension implementing t-digest aggregates for on-line "
        "accumulation of quantiles and trimmed means (tdigest_percentile, "
        "tdigest_digest, tdigest)"
    )
    license = "PostgreSQL"
    homepage = "https://github.com/tvondra/tdigest"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # A PostgreSQL extension module is dlopen-ed by the server; there is no
    # static-link form of the artifact.
    default_options = {"shared": True}

    def validate(self):
        # R32: accept both Linux and OHOS platform settings.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tdigest is only supported on Linux/OHOS, not {self.settings.os}")
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "tdigest is a PostgreSQL extension module and can only be built shared")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # PostgreSQL *server* headers + PGXS makefile + relocatable pg_config.
        # 18.3 is the version currently published in the ohpcd registry; the
        # extension builds and runs unchanged against it (upstream requires
        # PostgreSQL >= 13.0.0, see META.json prereqs).
        self.requires("postgresql/18.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # No patches are declared for 1.4.4 — upstream compiles unmodified on
        # OHOS — but the call is kept so that adding a patch later needs no
        # code change (and so the recipe stays uniform with the rest of the
        # archive). It is a no-op when conandata.yml has no `patches:` key.
        apply_conandata_patches(self)

    def build(self):
        # PGXS resolves every path (server includes, CFLAGS, install dirs)
        # through pg_config at make time, and the packaged pg_config is
        # relocatable (it derives the prefix from its own location), so the
        # build works wherever the conan cache lives.
        pg_bindir = self.dependencies["postgresql"].cpp_info.bindirs[0]
        pg_config = os.path.join(pg_bindir, "pg_config")
        # rpath= disables PGXS' default `-Wl,-rpath,'$(libdir)'` link flag
        # (Makefile.global: rpathdir = $(libdir)). For a server-side extension
        # module the rpath is meaningless — the module is dlopen-ed by the
        # postgres process and every PostgreSQL symbol is resolved in that
        # process — while the flag would bake the build machine's conan cache
        # path into the shipped .so (non-reproducible artifact / L5 baseline
        # churn). Only libc.so is left as DT_NEEDED.
        self.run(f'make PG_CONFIG="{pg_config}" rpath= -j1', cwd=self.source_folder)

    def package(self):
        # tdigest.so is the server module: the control file relies on the
        # default module_pathname ($libdir/tdigest), so the shared object is
        # deployed into the PostgreSQL pkglibdir by the consumer.
        copy(self, "tdigest.so", self.source_folder,
             os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "tdigest.control", self.source_folder,
             os.path.join(self.package_folder, "share", "extension"))
        copy(self, "tdigest--*.sql", self.source_folder,
             os.path.join(self.package_folder, "share", "extension"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["tdigest"]
        self.cpp_info.libdirs = ["lib"]
        # share/extension holds tdigest.control and the tdigest--*.sql scripts
        # that a PostgreSQL deployment copies into its sharedir.
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.set_property("cmake_file_name", "tdigest")
        self.cpp_info.set_property("cmake_target_name", "tdigest::tdigest")
