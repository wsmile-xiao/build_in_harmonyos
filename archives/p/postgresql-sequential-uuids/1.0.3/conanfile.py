#!/usr/bin/env python3
"""Conan recipe for postgresql-sequential-uuids 1.0.3.

Builds the sequential_uuids PostgreSQL extension module using the PGXS
build system. The extension generates sequential UUIDs to improve index
locality.

sequential_uuids is a PGXS extension: its Makefile does
``include $(shell $(PG_CONFIG) --pgxs)`` and sequential_uuids.c hard-includes
PostgreSQL *server* headers (postgres.h, commands/sequence.h, utils/uuid.h).

PostgreSQL 18.3 exists in this repo only as ``archives/p/postgresql/18.3/`` —
it is NOT a Conan package — so it cannot be declared as a ``tool_requires``.
This recipe therefore vendors the upstream postgresql-18.3.tar.bz2 and
bootstraps its own ``pg_config`` + PGXS + server headers + full server build
at build time.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, export_conandata_patches, patch


class PostgresqlSequentialUuidsConan(ConanFile):
    name = "postgresql-sequential-uuids"
    version = "1.0.3"
    description = "PostgreSQL extension generating sequential UUIDs for improved index locality"
    license = "PostgreSQL"
    homepage = "https://github.com/tvondra/sequential-uuids"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── PGXS bootstrap ────────────────────────────────────────────────────
    # Vendored PostgreSQL 18.3 source tree, configured and built to provide
    # pg_config + PGXS makefile snippet + server headers + full server
    # binaries (postgres/initdb/pg_ctl/createdb) for the test_package's
    # pg_regress harness.

    _TMPFS_ROOT = "/data/storage/el2/base/.pg-sequential-uuids-build"

    def _bootstrap_pgxs(self):
        pg_meta = self.conan_data["postgresql"]

        tmpfs_root = self._TMPFS_ROOT
        pg_src = os.path.join(tmpfs_root, "postgresql-18.3")
        pg_build = os.path.join(pg_src, "aarch64-build")
        pg_install = os.path.join(pg_src, "install")
        bootstrapped_pg_config = os.path.join(
            pg_build, "src", "bin", "pg_config", "pg_config")
        bootstrapped_postgres = os.path.join(pg_install, "bin", "postgres")

        # Idempotent: copy pgxs.mk + Makefile.shlib into build tree before guard
        pgxs_makefiles_dst = os.path.join(pg_build, "src", "makefiles")
        os.makedirs(pgxs_makefiles_dst, exist_ok=True)
        for fname in ("pgxs.mk",):
            _src = os.path.join(pg_src, "src", "makefiles", fname)
            _dst = os.path.join(pgxs_makefiles_dst, fname)
            if os.path.isfile(_src) and not os.path.isfile(_dst):
                shutil.copy2(_src, _dst)
        _shlib_src = os.path.join(pg_src, "src", "Makefile.shlib")
        _shlib_dst = os.path.join(pg_build, "src", "Makefile.shlib")
        if os.path.isfile(_shlib_src) and not os.path.isfile(_shlib_dst):
            shutil.copy2(_shlib_src, _shlib_dst)

        # Install PG server headers (idempotent, pre-guard)
        _makefile_global = os.path.join(pg_build, "src", "Makefile.global")
        _install_stamp = os.path.join(pg_build, ".pgxs-headers-installed")
        if (os.path.isfile(_makefile_global)
                and not os.path.isfile(_install_stamp)):
            _install_env = {
                "PATH": (
                    "/data/service/hnp/bin:"
                    "/storage/Users/currentUser/usr/local/bin:"
                    + os.environ.get("PATH", "/usr/bin:/bin")
                ),
                "HOME": os.environ.get("HOME", os.path.expanduser("~")),
                "TMPDIR": os.path.join(tmpfs_root, "tmp"),
                "TEMP": os.path.join(tmpfs_root, "tmp"),
                "TMP": os.path.join(tmpfs_root, "tmp"),
                "LANG": os.environ.get("LANG", "C.UTF-8"),
                "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
                "SHELL": os.environ.get("SHELL", "/bin/sh"),
            }
            for _k in ("USER", "LOGNAME", "TERM"):
                _v = os.environ.get(_k)
                if _v is not None:
                    _install_env[_k] = _v
            os.makedirs(_install_env["TMPDIR"], exist_ok=True)
            subprocess.run(
                ["make", f"-C{os.path.join('src', 'include')}",
                 "install", "-j1"],
                cwd=pg_build, env=_install_env, check=True,
            )
            with open(_install_stamp, "w", encoding="utf-8") as _fh:
                _fh.write("installed\n")

        # Guard: if pg_config + postgres are already built, skip full bootstrap
        if (os.path.isfile(bootstrapped_pg_config)
                and os.path.isfile(bootstrapped_postgres)):
            return pg_src

        # Stage the PG source on tmpfs
        os.makedirs(tmpfs_root, exist_ok=True)
        # Check for pre-downloaded tarball to avoid slow FTP download
        local_tarball = os.path.join(os.path.expanduser("~"), "tmp",
                                     "postgresql-18.3.tar.bz2")
        if os.path.isfile(local_tarball):
            # The tarball contains postgresql-18.3/ as top-level dir,
            # which is exactly pg_src. Extract directly into tmpfs_root.
            import tarfile
            with tarfile.open(local_tarball, "r:bz2") as tf:
                tf.extractall(path=tmpfs_root)
            if not os.path.isdir(pg_src):
                raise ConanException(
                    f"PG source not extracted to {pg_src} from {local_tarball}")
        else:
            os.makedirs(pg_src, exist_ok=True)
            get(self, **pg_meta, strip_root=True, destination=pg_src)

        # Apply the HarmonyOS adaptation patch
        patch_path = os.path.join(self.source_folder, "patches",
                                  "postgresql_harmony.patch")

        # Relax umask 077 → 067 in configure scripts
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

        # Apply HarmonyOS adaptation patch using Conan's patch_ng backend
        if os.path.isfile(patch_path):
            patch(self, base_path=pg_src, patch_file=patch_path,
                  strip=1, fuzz=False)

        # Configure PostgreSQL (no external deps needed)
        configure_cmd = [
            os.path.join(pg_src, "configure"),
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            f"--prefix={pg_install}",
            "--without-icu", "--without-readline",
            "--without-zlib", "--without-openssl",
        ]
        subprocess.run(configure_cmd, cwd=pg_build, env=clean_env, check=True)

        # Build pg_config
        subprocess.run(
            ["make", f"-C{os.path.join('src', 'bin', 'pg_config')}",
             "pg_config", "-j1"],
            cwd=pg_build, env=clean_env, check=True,
        )

        # Full PostgreSQL server build + install (needed for pg_regress)
        subprocess.run(["make", "-j1"], cwd=pg_build, env=clean_env, check=True)
        subprocess.run(
            ["make", "install", "-j1"], cwd=pg_build, env=clean_env, check=True,
        )

        # Re-copy pgxs.mk + Makefile.shlib after fresh configure
        pgxs_makefiles_dst = os.path.join(pg_build, "src", "makefiles")
        os.makedirs(pgxs_makefiles_dst, exist_ok=True)
        for fname in ("pgxs.mk",):
            _src = os.path.join(pg_src, "src", "makefiles", fname)
            _dst = os.path.join(pgxs_makefiles_dst, fname)
            if os.path.isfile(_src) and not os.path.isfile(_dst):
                shutil.copy2(_src, _dst)
        _shlib_src = os.path.join(pg_src, "src", "Makefile.shlib")
        _shlib_dst = os.path.join(pg_build, "src", "Makefile.shlib")
        if os.path.isfile(_shlib_src) and not os.path.isfile(_shlib_dst):
            shutil.copy2(_shlib_src, _shlib_dst)

        return pg_src

    def _find_pg_config(self):
        explicit = None
        try:
            explicit = self.conf.get("tools.build:pg_config", check_type=str)
        except ConanException:
            explicit = None
        if explicit and os.path.isfile(explicit):
            return explicit

        tmpfs_root = self._TMPFS_ROOT
        bootstrapped = os.path.join(
            tmpfs_root, "postgresql-18.3", "aarch64-build",
            "src", "bin", "pg_config", "pg_config")
        if os.path.isfile(bootstrapped):
            return bootstrapped

        candidates = []
        found = shutil.which("pg_config")
        if found:
            candidates.append(found)
        for prefix in (
            os.environ.get("PG_HOME", ""),
            "/usr/local/pgsql",
            "/usr/lib/postgresql",
        ):
            if prefix:
                candidates.append(os.path.join(prefix, "bin", "pg_config"))
        candidates.append(os.path.join(
            os.path.expanduser("~/usr/local/bin"), "pg_config"))
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand

        raise ConanException(
            "pg_config not found. The recipe tried to bootstrap one from the "
            "vendored postgresql-18.3 source tree but failed; PostgreSQL "
            "server development files (postgres.h, PGXS) are required "
            "to build sequential_uuids.")

    def generate(self):
        pass

    def build(self):
        # NOTE: the vendored postgresql_harmony.patch targets the PostgreSQL
        # 18.3 source tree (src/backend/..., src/include/...), NOT the
        # sequential_uuids sources.  It is applied manually inside
        # _bootstrap_pgxs() via ``patch()``; calling
        # apply_conandata_patches() here would try to patch the
        # sequential_uuids tree and fail (target files don't exist).

        pg_src = self._bootstrap_pgxs()
        pg_config = self._find_pg_config()

        tmpfs_root = self._TMPFS_ROOT
        pg_build = os.path.join(
            tmpfs_root, "postgresql-18.3", "aarch64-build")
        pgxs_path = os.path.join(
            pg_build, "src", "makefiles", "pgxs.mk")

        make_env = os.environ.copy()
        make_env.update({
            "PATH": (
                "/data/service/hnp/bin:"
                "/storage/Users/currentUser/usr/local/bin:"
                + os.environ.get("PATH", "/usr/bin:/bin")
            ),
            "PG_CONFIG": pg_config,
            # PG_LDFLAGS: ld.lld-supported flags that resolve undefined PG
            # server symbols to zero at link time. The extension .so has
            # undefined refs to PG server core symbols (palloc,
            # pg_strong_random, nextval_internal, ereport, elog, etc.) that
            # are resolved by the postgres server at CREATE EXTENSION load.
            "PG_LDFLAGS": (
                "-Wl,--unresolved-symbols=ignore-all "
                "-Wl,--allow-shlib-undefined"
            ),
            "PGXS": pgxs_path,
        })

        subprocess.run(
            ["make", f"PG_CONFIG={pg_config}", f"PGXS={pgxs_path}", "-j1"],
            cwd=self.build_folder, env=make_env, check=True,
        )

    def package(self):
        # Extension .so
        copy(self, "sequential_uuids.so", self.build_folder,
             os.path.join(self.package_folder, "lib"))
        # Extension control + SQL files
        copy(self, "*.control", self.source_folder,
             os.path.join(self.package_folder, "extension"))
        copy(self, "*.sql", self.source_folder,
             os.path.join(self.package_folder, "extension"))

        # Vendor the upstream source tree into the package for test_package
        upstream_dst = os.path.join(self.package_folder, "upstream")
        for item in ("Makefile", "sequential_uuids.c",
                     "sequential_uuids.control",
                     "sequential_uuids--1.0.1.sql",
                     "sequential_uuids--1.0--1.0.1.sql",
                     "sequential_uuids--1.0.1--1.0.2.sql",
                     "sequential_uuids--1.0.2--1.0.3.sql",
                     "test"):
            src = os.path.join(self.source_folder, item)
            if os.path.isdir(src):
                copy(self, "*", src, os.path.join(upstream_dst, item))
            elif os.path.isfile(src):
                copy(self, item, self.source_folder, upstream_dst)

    def package_info(self):
        self.cpp_info.libs = ["sequential_uuids"]
        self.cpp_info.libdirs = ["lib"]
