"""Conan recipe for postgresql-pllua REL_2_0_12 (PL/Lua PostgreSQL extension).

Builds the pllua/plluau PostgreSQL extensions using PGXS. The extension
embeds Lua as a procedural language for PostgreSQL, allowing users to
write SQL functions in Lua.

Build system: PGXS (PostgreSQL Extension Makefile), which requires:
  - PostgreSQL server development tree (pg_config + PGXS + server headers)
  - Lua library + headers + interpreter/compiler (for build-time codegen)

Both PostgreSQL 18.3 and Lua 5.4.8 are vendored from source and built
at recipe build time, mirroring the proven archives/p/postgresql-topn/2.7.0
pattern. No conan dependencies are needed (self-contained build).
"""
import os
import shutil
import subprocess
import glob

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, export_conandata_patches, patch


class PostgresqlPlluaConan(ConanFile):
    name = "postgresql-pllua"
    version = "2.0.12"
    description = "Lua as a procedural language for PostgreSQL"
    license = "PostgreSQL"
    homepage = "https://github.com/pllua/pllua"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    _TMPFS_ROOT = "/data/storage/el2/base/.postgresql-pllua-build"
    _PG_VERSION = "18.3"
    _LUA_VERSION = "5.4.8"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _bootstrap_pgxs(self):
        """Bootstrap a full PostgreSQL server from the vendored source tree.

        Mirrors archives/p/postgresql-topn/2.7.0/conanfile.py: download PG 18.3,
        apply the HarmonyOS adaptation patch, configure, make, make install.
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

        # Idempotent: skip if already bootstrapped
        if (os.path.isfile(bootstrapped_pg_config)
                and os.path.isfile(bootstrapped_postgres)):
            return pg_src

        os.makedirs(tmpfs_root, exist_ok=True)
        os.makedirs(pg_src, exist_ok=True)
        get(self, **pg_meta, strip_root=True, destination=pg_src)

        # Relax umask 077 -> 067 across configure wrappers
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

        # Full server build: make + make install
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

        # Copy pgxs.mk + Makefile.shlib into build tree
        pgxs_makefiles_dst = os.path.join(pg_build, "src", "makefiles")
        os.makedirs(pgxs_makefiles_dst, exist_ok=True)
        for src_name in ("pgxs.mk", "Makefile.shlib"):
            _src = os.path.join(pg_src, "src", "makefiles", src_name)
            _dst = os.path.join(pgxs_makefiles_dst, src_name)
            if os.path.isfile(_src) and not os.path.isfile(_dst):
                shutil.copy2(_src, _dst)

        # Copy config/ directory (install-sh etc.) into build tree
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

    def _bootstrap_lua(self):
        """Build Lua 5.4.8 from vendored source (static library + interpreter).

        Produces liblua.a, lua, luac, and headers in a dedicated install dir.
        """
        lua_meta = self.conan_data["lua"]
        tmpfs_root = self._TMPFS_ROOT
        lua_src = os.path.join(tmpfs_root, "lua-5.4.8")
        lua_install = os.path.join(tmpfs_root, "lua-install")
        bootstrapped_lua = os.path.join(lua_install, "bin", "lua")
        bootstrapped_luac = os.path.join(lua_install, "bin", "luac")
        bootstrapped_lib = os.path.join(lua_install, "lib", "liblua.a")

        # Idempotent: skip if already bootstrapped
        if (os.path.isfile(bootstrapped_lua)
                and os.path.isfile(bootstrapped_luac)
                and os.path.isfile(bootstrapped_lib)):
            return lua_install

        os.makedirs(lua_src, exist_ok=True)
        os.makedirs(lua_install, exist_ok=True)
        os.makedirs(os.path.join(lua_install, "bin"), exist_ok=True)
        os.makedirs(os.path.join(lua_install, "lib"), exist_ok=True)
        os.makedirs(os.path.join(lua_install, "include"), exist_ok=True)

        get(self, **lua_meta, strip_root=True, destination=lua_src)

        lua_src_inner = os.path.join(lua_src, "src")
        tmpfs_tmp = os.path.join(tmpfs_root, "tmp")
        os.makedirs(tmpfs_tmp, exist_ok=True)

        build_env = {
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
        }
        for k in ("USER", "LOGNAME", "TERM"):
            v = os.environ.get(k)
            if v is not None:
                build_env[k] = v

        cc = "/data/service/hnp/bin/clang"
        ar = "/data/service/hnp/bin/llvm-ar"
        ranlib = "/data/service/hnp/bin/llvm-ranlib"
        cflags = "-O3 -fPIC -DLUA_USE_POSIX -DLUA_USE_DLOPEN"

        # Build Lua generic target
        make_args = (
            f'CC="{cc}" '
            f'AR="{ar} rcu" '
            f'RANLIB="{ranlib}" '
            f'MYCFLAGS="{cflags}" MYLIBS="-ldl -lm"'
        )
        subprocess.run(
            f'make -C "{lua_src_inner}" -j1 generic {make_args}',
            shell=True, env=build_env, check=True,
        )
        # Run Lua test (validates the build)
        subprocess.run(
            f'make -C "{lua_src_inner}" test {make_args}',
            shell=True, env=build_env, check=True,
        )

        # Install: copy headers, lib, and binaries
        for hdr in ("lua.h", "lualib.h", "lauxlib.h", "luaconf.h",
                     "lua.hpp"):
            src_h = os.path.join(lua_src_inner, hdr)
            if os.path.isfile(src_h):
                shutil.copy2(src_h, os.path.join(lua_install, "include", hdr))

        lib_src = os.path.join(lua_src_inner, "liblua.a")
        if os.path.isfile(lib_src):
            shutil.copy2(lib_src, os.path.join(lua_install, "lib", "liblua.a"))

        for bin_name in ("lua", "luac"):
            bin_src = os.path.join(lua_src_inner, bin_name)
            if os.path.isfile(bin_src):
                shutil.copy2(bin_src, os.path.join(lua_install, "bin", bin_name))

        return lua_install

    def _find_pg_config(self):
        """Locate the bootstrapped pg_config binary."""
        tmpfs_root = self._TMPFS_ROOT
        bootstrapped = os.path.join(
            tmpfs_root, f"postgresql-{self._PG_VERSION}", "aarch64-build",
            "src", "bin", "pg_config", "pg_config")
        if os.path.isfile(bootstrapped):
            return bootstrapped

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

        pgxs.mk is at pg_build/src/makefiles/pgxs.mk and references
        ../../src/Makefile.shlib (resolves to pg_build/src/Makefile.shlib).
        Makefile.shlib lives in src/ (not src/makefiles/) in the PG source.
        """
        # 1. Copy pgxs.mk to pg_build/src/makefiles/
        pgxs_dst = os.path.join(pg_build, "src", "makefiles")
        os.makedirs(pgxs_dst, exist_ok=True)
        for src_name in ("pgxs.mk", "Makefile.shlib"):
            _src = os.path.join(pg_src, "src", "makefiles", src_name)
            _dst = os.path.join(pgxs_dst, src_name)
            if os.path.isfile(_src) and not os.path.isfile(_dst):
                shutil.copy2(_src, _dst)
            if not os.path.isfile(_dst):
                _inst = os.path.join(
                    pg_src, "install", "lib", "pgxs", "src",
                    "makefiles", src_name)
                if os.path.isfile(_inst):
                    shutil.copy2(_inst, _dst)

        # 2. Copy Makefile.shlib to pg_build/src/ (where pgxs.mk expects it)
        shlib_dst = os.path.join(pg_build, "src", "Makefile.shlib")
        if not os.path.isfile(shlib_dst):
            # Try source tree first (src/Makefile.shlib)
            shlib_src = os.path.join(pg_src, "src", "Makefile.shlib")
            if os.path.isfile(shlib_src):
                shutil.copy2(shlib_src, shlib_dst)
            else:
                # Try install tree
                shlib_inst = os.path.join(
                    pg_src, "install", "lib", "pgxs", "src",
                    "Makefile.shlib")
                if os.path.isfile(shlib_inst):
                    shutil.copy2(shlib_inst, shlib_dst)
                else:
                    # Try makefiles dir (some PG versions put it there)
                    shlib_mk = os.path.join(
                        pg_src, "src", "makefiles", "Makefile.shlib")
                    if os.path.isfile(shlib_mk):
                        shutil.copy2(shlib_mk, shlib_dst)

        # 3. Copy config/ directory (install-sh, mkinstalldirs, etc.)
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
        # NOTE: Patches are NOT auto-applied via apply_conandata_patches()
        # because the postgresql_harmony.patch targets the vendored PG source
        # tree, not the pllua sources. It is applied in _bootstrap_pgxs().
        # The pllua-specific patch (pg18 noreturn compat) is applied here.

        # Apply pllua-specific patches to the pllua source
        pllua_patch = os.path.join(self.source_folder, "patches",
                                    "0002-pllua-pg18-noreturn-compat.patch")
        if os.path.isfile(pllua_patch):
            patch(self, base_path=self.build_folder,
                  patch_file=pllua_patch, strip=1, fuzz=False)

        # Bootstrap full PG server (pg_config + PGXS + server headers + binaries)
        pg_src = self._bootstrap_pgxs()
        pg_config = self._find_pg_config()

        # Bootstrap Lua 5.4.8 (headers + liblua.a + lua/luac binaries)
        lua_install = self._bootstrap_lua()
        lua_inadir = os.path.join(lua_install, "include")
        lua_libdir = os.path.join(lua_install, "lib")
        lua_bin = os.path.join(lua_install, "bin", "lua")
        luac_bin = os.path.join(lua_install, "bin", "luac")

        tmpfs_root = self._TMPFS_ROOT
        pg_build = os.path.join(
            tmpfs_root, f"postgresql-{self._PG_VERSION}", "aarch64-build")
        pgxs_path = os.path.join(pg_build, "src", "makefiles", "pgxs.mk")

        # Ensure pgxs.mk is in the build tree (idempotent)
        self._ensure_pgxs_layout(pg_build, pg_src)

        # Build the extension using PGXS
        make_env = os.environ.copy()
        make_env.update({
            "PATH": (
                "/data/service/hnp/bin:"
                "/storage/Users/currentUser/usr/local/bin:"
                + os.environ.get("PATH", "/usr/bin:/bin")
            ),
            "PG_CONFIG": pg_config,
            "PGXS": pgxs_path,
            "LUA_INCDIR": lua_inadir,
            "LUALIB": f"-L{lua_libdir} -llua -ldl -lm",
            "LUA": lua_bin,
            "LUAC": luac_bin,
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
        for k in ("USER", "LOGNAME", "TERM"):
            v = os.environ.get(k)
            if v is not None:
                make_env[k] = v

        # make: builds pllua.so + generates headers via Lua scripts
        # BIN_LD: ld.lld needs -m aarch64linux for -r -b binary (embedding .luac)
        bin_ld = "/data/service/hnp/bin/ld.lld -r -b binary -m aarch64linux"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        subprocess.run(
            ["make", f"PG_CONFIG={pg_config}", f"PGXS={pgxs_path}",
             f"LUA_INCDIR={lua_inadir}", f"LUALIB=-L{lua_libdir} -llua -ldl -lm",
             f"LUA={lua_bin}", f"LUAC={luac_bin}",
             f"BIN_LD={bin_ld}", f"OBJCOPY={objcopy}", "-j1"],
            cwd=self.build_folder, env=make_env, check=True,
        )

    def package(self):
        # Copy pllua.so (the shared library)
        copy(self, "*.so", self.build_folder,
             os.path.join(self.package_folder, "lib"))

        # Copy control files
        copy(self, "*.control", self.source_folder,
             os.path.join(self.package_folder, "extension"))

        # Copy SQL files from scripts/ directory
        copy(self, "*.sql", os.path.join(self.source_folder, "scripts"),
             os.path.join(self.package_folder, "extension"))

        # Vendor the upstream source tree for test_package's pg_regress harness
        upstream_dst = os.path.join(self.package_folder, "upstream")
        for item in ("Makefile", "serial_schedule", "parallel_schedule",
                     "pllua.control", "plluau.control", "src", "scripts",
                     "sql", "expected", "tools"):
            src = os.path.join(self.source_folder, item)
            if os.path.isdir(src):
                copy(self, "*", src, os.path.join(upstream_dst, item))
            elif os.path.isfile(src):
                copy(self, item, self.source_folder, upstream_dst)

    def package_info(self):
        self.cpp_info.libs = ["pllua"]
        self.cpp_info.libdirs = ["lib"]
