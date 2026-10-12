"""Conan recipe for orafce 4.16.7 (Oracle compatibility extension).

Builds the orafce PostgreSQL extension with PGXS. orafce is a classic PGXS
extension: its Makefile does ``PGXS := $(shell $(PG_CONFIG) --pgxs)`` and
``include $(PGXS)``. The extension ships server-side C sources
(postgres.h, fmgr.h, ...) and links against the PostgreSQL server, so the
full server headers + PGXS from the prebuilt ``postgresql/18.3`` package are
required (no source bootstrap needed -- the binary package is consumable and
ships pg_config, server headers, PGXS and the server binaries).

The prebuilt ``postgresql/18.3`` (OHOS aarch64) dependency is the forced
third-party dependency declared by the upstream dependency probe (W0): it is
CONSUMABLE via ``conan download`` and provides everything PGXS needs, plus
postgres/initdb/pg_ctl/createdb/psql so the test_package can drive the
upstream pg_regress suite against a live server.

The extension ``.so`` carries undefined PostgreSQL server symbols that are
resolved at ``CREATE EXTENSION`` load time, so we link with
``--unresolved-symbols=ignore-all --allow-shlib-undefined`` (ld.lld).
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches


class PostgresqlOrafceConan(ConanFile):
    name = "orafce"
    version = "4.16.7"
    description = "Oracle compatibility functions for PostgreSQL"
    license = "PostgreSQL"
    homepage = "https://github.com/orafce/orafce"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    _PG_VERSION = "18.3"

    def export_sources(self):
        # No patches: orafce compiles on OHOS without source changes.
        pass

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."

    def requirements(self):
        self.requires("postgresql/18.3")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _pg_paths(self):
        pg = self.dependencies["postgresql"]
        bindir = pg.cpp_info.bindirs[0]
        pg_config = os.path.join(bindir, "pg_config")
        pgxs = subprocess.check_output(
            [pg_config, "--pgxs"], text=True).strip()
        return bindir, pg_config, pgxs

    def build(self):
        # orafce ships no upstream patches; apply only if conandata declares a
        # "patches" section. The G1 gate requires the call site to be present,
        # but apply_conandata_patches is a safe no-op without patches.
        if "patches" in self.conan_data:
            apply_conandata_patches(self)

        # Bypass Conan's self.run() to avoid the conanbuild.sh launcher
        # re-injecting a polluted CC/CFLAGS that break PGXS compile probes.
        bindir, pg_config, pgxs = self._pg_paths()
        make_env = os.environ.copy()
        make_env.update({
            "PATH": (
                bindir + ":/data/service/hnp/bin:"
                "/storage/Users/currentUser/usr/local/bin:"
                + make_env.get("PATH", "/usr/bin:/bin")
            ),
            "PG_CONFIG": pg_config,
            "PGXS": pgxs,
            "CC": "/data/service/hnp/bin/clang",
            "CXX": "/data/service/hnp/bin/clang++",
            # PG server symbols are undefined until the postgres process
            # loads the extension at CREATE EXTENSION time.
            "PG_LDFLAGS": (
                "-Wl,--unresolved-symbols=ignore-all "
                "-Wl,--allow-shlib-undefined"
            ),
        })
        for k in ("HOME", "LANG", "LC_ALL", "SHELL", "TMPDIR", "TEMP", "TMP"):
            v = os.environ.get(k)
            if v is not None:
                make_env[k] = v

        # Build the extension .so with PGXS.
        subprocess.run(
            ["make", f"PG_CONFIG={pg_config}", f"PGXS={pgxs}", "-j1"],
            cwd=self.source_folder, env=make_env, check=True)

    def package(self):
        # orafce.so
        copy(self, "orafce.so", self.build_folder,
             os.path.join(self.package_folder, "lib"))

        # Extension control + SQL definitions (control file + base + upgrade)
        copy(self, "orafce.control", self.source_folder,
             os.path.join(self.package_folder, "extension"))
        copy(self, "orafce--*.sql", self.source_folder,
             os.path.join(self.package_folder, "extension"))

        # Vendor the upstream source tree so the test_package can drive the
        # upstream pg_regress suite (sql/expected + Makefile + PGXS build).
        upstream_dst = os.path.join(self.package_folder, "upstream")
        copy(self, "*", self.source_folder, upstream_dst)

    def package_info(self):
        self.cpp_info.libs = ["orafce"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.resdirs = ["extension"]
