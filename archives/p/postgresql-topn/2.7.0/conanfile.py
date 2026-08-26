"""Conan recipe for postgresql-topn 2.7.0 (PostgreSQL Top-N extension).

Builds the topn PostgreSQL extension using PGXS. The extension provides
approximate top-N query aggregation using the SpaceSaving algorithm.

postgresql-topn is a PGXS extension: its Makefile does
``PGXS := $(shell $(PG_CONFIG) --pgxs)`` / ``include $(PGXS)`` and topn.c
hard-includes PostgreSQL *server* headers (postgres.h, fmgr.h, utils/guc.h,
access/hash.h, ...). libpq only ships client-side headers, so a full
PostgreSQL server development tree is required.

PostgreSQL 18.3 is vendored from source and bootstrapped (configure + make +
make install) at build time, mirroring the proven
archives/a/address-standardizer/3.7.0 recipe and archives/p/postgresql/18.3/
build.sh path. The full server build provides pg_config + PGXS + server
headers for compiling, and postgres/initdb/pg_ctl/createdb for test_package
to drive pg_regress (8 test groups: add_agg, union_agg, char_tests,
null_tests, add_union_tests, copy_data, customer_reviews_query, join_tests).
"""
import os
import shutil
import subprocess
import glob

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, export_conandata_patches, patch


class PostgresqlTopnConan(ConanFile):
    name = "postgresql-topn"
    version = "2.7.0"
    description = "PostgreSQL extension for fast top-N queries using approximate algorithm"
    license = "PostgreSQL"
    homepage = "https://github.com/citusdata/postgresql-topn"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    _TMPFS_ROOT = "/data/storage/el2/base/.postgresql-topn-build"
    _PG_VERSION = "18.3"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _bootstrap_pgxs(self):
        """Bootstrap a full PostgreSQL server from the vendored source tree.

        Mirrors archives/a/address-standardizer/3.7.0/conanfile.py and
        archives/p/postgresql/18.3/build.sh: download PG 18.3, apply the
        HarmonyOS adaptation patch, configure, make, make install.
        The full server build provides pg_config + PGXS + server headers
        for compiling the extension, and postgres/initdb/pg_ctl/createdb
        for test_package to drive pg_regress.
        """
        pg_meta = self.conan_data["postgresql"]
        tmpfs_root = self._TMPFS_ROOT
        pg_src = os.path.join(tmpfs_root, f"postgresql-{self._PG_VERSION}")
        pg_build = os.path.join(pg_src, "aarch64-build")
        pg_install = os.path.join(pg_src, "install")
        bootstrapped_pg_config = os.path.join(
            pg_build, "src", "bin", "pg_config", "pg_config")
        bootstrapped_postgres = os.path.join(
            pg_install, "bin", "postgres")

        # Idempotent: skip if already bootstrapped (persistent tmpfs across rounds)
        if (os.path.isfile(bootstrapped_pg_config)
                and os.path.isfile(bootstrapped_postgres)):
            return pg_src

        os.makedirs(tmpfs_root, exist_ok=True)
        os.makedirs(pg_src, exist_ok=True)
        get(self, **pg_meta, strip_root=True, destination=pg_src)

        # Relax umask 077 -> 067 across configure wrappers (same as PG 18.3 build.sh)
        for root, _dirs, files in os.walk(pg_src):
            for name in files:
                if name == "configure":
                    cfg_path = os.path.join(root, name)
                    try:
                        with open(cfg_path, "r", encoding="utf-8",
                                  errors="surrogateescape") as fh:
                            text = fh.read()
                        new_text = text.replace("umask 077", "umask 067")
                        if new_text != text:
                            with open(cfg_path, "w", encoding="utf-8",
                                      errors="surrogateescape") as fh:
                                fh.write(new_text)
                    except OSError:
                        pass

        os.makedirs(pg_build, exist_ok=True)
        os.makedirs(pg_install, exist_ok=True)

        tmpfs_tmp = os.path.join(tmpfs_root, "tmp")
        os.makedirs(tmpfs_tmp, exist_ok=True)
        clean_env = {
            "PATH": (
                "/data/service/hnp/bin:"
                "/storage/Users/currentUser/usr/local/bin:"
                + os.environ.get("PATH", "/usr/bin:/bin")
            ),
            "HOME": os.environ.get("HOME", os.path.expanduser("~")),
            "TMPDIR": tmpfs_tmp,
            "TEMP": tmpfs_tmp,
            "TMP": tmpfs_tmp,
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
            "SHELL": os.environ.get("SHELL", "/bin/sh"),
            "CC": "/data/service/hnp/bin/clang",
            "CXX": "/data/service/hnp/bin/clang++",
        }
        for k in ("USER", "LOGNAME", "TERM"):
            v = os.environ.get(k)
            if v is not None:
                clean_env[k] = v

        # Apply HarmonyOS adaptation patch
        patch_path = os.path.join(self.source_folder, "patches",
                                  "0001-postgresql-harmony.patch")
        if os.path.isfile(patch_path):
            patch(self, base_path=pg_src, patch_file=patch_path,
                  strip=1, fuzz=False)

        # Configure (minimal --without-* flags keep it cheap)
        configure_cmd = [
            os.path.join(pg_src, "configure"),
            f"--prefix={pg_install}",
            "--without-icu", "--without-readline",
            "--without-zlib", "--without-openssl",
        ]
        subprocess.run(configure_cmd, cwd=pg_build, env=clean_env, check=True)

        # Full server build: make + make install (provides postgres/initdb/pg_ctl)
        subprocess.run(["make", "-j1"], cwd=pg_build, env=clean_env, check=True)
        subprocess.run(["make", "install", "-j1"], cwd=pg_build,
                       env=clean_env, check=True)

        # Install server headers (needed by PGXS for extension compilation)
        makefile_global = os.path.join(pg_build, "src", "Makefile.global")
        install_stamp = os.path.join(pg_build, ".pgxs-headers-installed")
        if os.path.isfile(makefile_global) and not os.path.isfile(install_stamp):
            install_env = dict(clean_env)
            subprocess.run(
                ["make", f"-C{os.path.join('src', 'include')}",
                 "install", "-j1"],
                cwd=pg_build, env=install_env, check=True,
            )
            with open(install_stamp, "w", encoding="utf-8") as fh:
                fh.write("installed\n")

        # Copy pgxs.mk + Makefile.shlib into build tree (same as address-standardizer)
        pgxs_makefiles_dst = os.path.join(pg_build, "src", "makefiles")
        os.makedirs(pgxs_makefiles_dst, exist_ok=True)
        for src_name in ("pgxs.mk", "Makefile.shlib"):
            _src = os.path.join(pg_src, "src", "makefiles", src_name)
            _dst = os.path.join(pgxs_makefiles_dst, src_name)
            if os.path.isfile(_src) and not os.path.isfile(_dst):
                shutil.copy2(_src, _dst)

        # Copy config/ directory (install-sh etc.) into build tree
        # Can't use copytree because config/ already exists with Makefile
        config_dst = os.path.join(pg_build, "config")
        config_src = os.path.join(pg_src, "config")
        if os.path.isdir(config_src):
            os.makedirs(config_dst, exist_ok=True)
            for cf in os.listdir(config_src):
                _cs = os.path.join(config_src, cf)
                _cd = os.path.join(config_dst, cf)
                if os.path.isfile(_cs) and not os.path.isfile(_cd):
                    shutil.copy2(_cs, _cd)

        return pg_src

    def _find_pg_config(self):
        """Locate the bootstrapped pg_config binary."""
        tmpfs_root = self._TMPFS_ROOT
        bootstrapped = os.path.join(
            tmpfs_root, f"postgresql-{self._PG_VERSION}", "aarch64-build",
            "src", "bin", "pg_config", "pg_config")
        if os.path.isfile(bootstrapped):
            return bootstrapped

        # Fallback: system discovery
        found = shutil.which("pg_config")
        if found:
            return found
        for prefix in (
            os.environ.get("PG_HOME", ""),
            "/usr/local/pgsql",
            "/usr/lib/postgresql",
        ):
            if prefix:
                cand = os.path.join(prefix, "bin", "pg_config")
                if cand and os.path.isfile(cand):
                    return cand

        raise ConanException(
            "pg_config not found. The recipe tried to bootstrap one from "
            "the vendored postgresql-18.3 source tree but failed.")

    def _ensure_pgxs_layout(self, pg_build, pg_src):
        """Copy pgxs.mk + Makefile.shlib + config/ into the build tree.

        Called from build() right before the extension make, to ensure
        the PGXS layout is present even if _bootstrap_pgxs() returned
        early from the idempotent guard.
        """
        pgxs_dst = os.path.join(pg_build, "src", "makefiles")
        os.makedirs(pgxs_dst, exist_ok=True)
        for src_name in ("pgxs.mk", "Makefile.shlib"):
            _src = os.path.join(pg_src, "src", "makefiles", src_name)
            _dst = os.path.join(pgxs_dst, src_name)
            if os.path.isfile(_src) and not os.path.isfile(_dst):
                shutil.copy2(_src, _dst)
            # Also check install tree (make install copies makefiles/)
            if not os.path.isfile(_dst):
                _inst = os.path.join(
                    pg_src, "install", "lib", "pgxs", "src",
                    "makefiles", src_name)
                if os.path.isfile(_inst):
                    shutil.copy2(_inst, _dst)
        # Copy config/ directory (install-sh, mkinstalldirs, etc.)
        # pgxs.mk references $(top_builddir)/config/install-sh
        config_dst = os.path.join(pg_build, "config")
        config_src = os.path.join(pg_src, "config")
        if os.path.isdir(config_src):
            os.makedirs(config_dst, exist_ok=True)
            for cf in os.listdir(config_src):
                _cs = os.path.join(config_src, cf)
                _cd = os.path.join(config_dst, cf)
                if os.path.isfile(_cs) and not os.path.isfile(_cd):
                    shutil.copy2(_cs, _cd)

    def generate(self):
        pass

    def build(self):
        # NOTE: we do NOT call apply_conandata_patches() here because the
        # postgresql_harmony.patch targets the vendored PostgreSQL 18.3
        # source tree (src/backend/..., src/include/...), NOT the
        # postgresql-topn sources. It is applied manually inside
        # _bootstrap_pgxs() via patch().

        # Bootstrap full PG server (pg_config + PGXS + server headers + server binaries)
        pg_src = self._bootstrap_pgxs()
        pg_config = self._find_pg_config()

        tmpfs_root = self._TMPFS_ROOT
        pg_build = os.path.join(
            tmpfs_root, f"postgresql-{self._PG_VERSION}", "aarch64-build")
        pgxs_path = os.path.join(pg_build, "src", "makefiles", "pgxs.mk")

        # Ensure pgxs.mk is in the build tree (idempotent, handles early-return)
        self._ensure_pgxs_layout(pg_build, pg_src)

        # Build the extension using PGXS
        # Bypass Conan's self.run() to avoid conanbuild.sh launcher re-injecting
        # polluted CC/CFLAGS that break PGXS compile probes.
        make_env = os.environ.copy()
        make_env.update({
            "PATH": (
                "/data/service/hnp/bin:"
                "/storage/Users/currentUser/usr/local/bin:"
                + os.environ.get("PATH", "/usr/bin:/bin")
            ),
            "PG_CONFIG": pg_config,
            "PGXS": pgxs_path,
            # PG server symbols are undefined until the postgres process
            # loads the extension at CREATE EXTENSION time. Use ld.lld-supported
            # flags to resolve them to zero at link time.
            "PG_LDFLAGS": (
                "-Wl,--unresolved-symbols=ignore-all "
                "-Wl,--allow-shlib-undefined"
            ),
        })
        for k in ("HOME", "LANG", "LC_ALL", "SHELL", "TMPDIR", "TEMP", "TMP"):
            v = os.environ.get(k)
            if v is not None:
                make_env[k] = v
        for k in ("USER", "LOGNAME", "TERM"):
            v = os.environ.get(k)
            if v is not None:
                make_env[k] = v

        # make: builds topn.so + generates SQL files from update/ via cpp
        # The Makefile's SQLPP uses `cpp` which is not on PATH; use clang -E
        pg_install = os.path.join(
            tmpfs_root, f"postgresql-{self._PG_VERSION}", "install")
        pg_config_h = os.path.join(
            pg_install, "include", "server", "pg_config.h")
        sqlpp = f"/data/service/hnp/bin/clang -E -undef -w -P -imacros {pg_config_h}"
        subprocess.run(
            ["make", f"PG_CONFIG={pg_config}", f"PGXS={pgxs_path}",
             f"SQLPP={sqlpp}", "-j1"],
            cwd=self.build_folder, env=make_env, check=True,
        )

    def package(self):
        # Copy topn.so
        copy(self, "*.so", self.build_folder,
             os.path.join(self.package_folder, "lib"))

        # Copy control file + generated SQL files
        copy(self, "*.control", self.source_folder,
             os.path.join(self.package_folder, "extension"))
        # Generated SQL files are in the build folder root (topn--*.sql)
        for sql_file in glob.glob(os.path.join(self.build_folder, "topn--*.sql")):
            copy(self, os.path.basename(sql_file),
                 os.path.dirname(sql_file),
                 os.path.join(self.package_folder, "extension"))

        # Also copy update/ SQL templates (for test_package to regenerate if needed)
        copy(self, "*.sql", os.path.join(self.source_folder, "update"),
             os.path.join(self.package_folder, "extension", "update"))

        # Vendor the upstream source tree for test_package's pg_regress harness
        upstream_dst = os.path.join(self.package_folder, "upstream")
        for item in ("Makefile", "topn.c", "topn.control", "update",
                     "sql", "expected", "test_data_provider", "data"):
            src = os.path.join(self.source_folder, item)
            if os.path.isdir(src):
                copy(self, "*", src, os.path.join(upstream_dst, item))
            elif os.path.isfile(src):
                copy(self, item, self.source_folder, upstream_dst)
        # Also copy the generated SQL files into upstream/ (pg_regress needs them)
        for sql_file in glob.glob(os.path.join(self.build_folder, "topn--*.sql")):
            copy(self, os.path.basename(sql_file),
                 os.path.dirname(sql_file), upstream_dst)

    def package_info(self):
        self.cpp_info.libs = ["topn"]
        self.cpp_info.libdirs = ["lib"]
