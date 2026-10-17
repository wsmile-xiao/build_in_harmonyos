#!/usr/bin/env python3
"""Conan recipe for luasql 2.4.0 — Lua SQL database access library.

LuaSQL is a Lua extension module providing database access via SQLite3 driver.
Since lua and sqlite3 are not available as conan packages in the registry,
this recipe builds them from source as part of the build process.

On HarmonyOS (OHOS), Lua extension modules require explicit linking to
the Lua library (-llua) since the platform does not support dynamic symbol
export from the host interpreter.
"""
import os
import shutil
import hashlib
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LuasqlConan(ConanFile):
    name = "luasql"
    version = "2.4.0"
    description = "LuaSQL is a simple interface from Lua to a DBMS"
    license = "MIT"
    homepage = "https://github.com/lunarmodules/luasql"
    url = ""

    package_type = "library"

    # R32: settings.os check must use "OHOS" not "Linux"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # Self-contained: lua and sqlite3 built from source in build()

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _is_ohos(self):
        return self.settings.os == "OHOS"

    def _get_cc(self):
        # R33: Get compiler from Conan conf, not undefined shell variables
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return comp_execs.get("c") or "clang"

    def _get_ar(self):
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return comp_execs.get("ar") or "llvm-ar"

    def _get_ranlib(self):
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return comp_execs.get("ranlib") or "llvm-ranlib"

    def _sign_elf(self, path):
        """Sign ELF binary on OHOS for execution on HarmonyOS."""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if Path(sign_tool).exists():
            self.run(
                f'{objcopy} --remove-section .codesign "{path}" || true'
            )
            self.run(
                f'{sign_tool} sign -inFile "{path}" '
                f'-outFile "{path}.signed" -selfSign 1'
            )
            shutil.move(f"{path}.signed", path)
        os.chmod(path, 0o755)

    def _download(self, url, dest):
        """Download a file using curl (CI workers may lack Python ssl)."""
        self.run(f'curl -L -sS --fail -o "{dest}" "{url}"')

    def _verify_sha256(self, path, expected):
        """Verify SHA256 checksum of a file."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        actual = h.hexdigest()
        if actual != expected:
            raise RuntimeError(
                f"SHA256 mismatch: expected {expected}, got {actual}"
            )

    def build(self):
        apply_conandata_patches(self)

        cc = self._get_cc()
        ar = self._get_ar()
        ranlib = self._get_ranlib()
        is_ohos = self._is_ohos()
        ld_flag = "-fuse-ld=/data/service/hnp/bin/ld" if is_ohos else ""

        src = self.source_folder
        build_dir = self.build_folder
        local_prefix = os.path.join(build_dir, "local_install")
        os.makedirs(os.path.join(local_prefix, "bin"), exist_ok=True)
        os.makedirs(os.path.join(local_prefix, "include"), exist_ok=True)
        os.makedirs(os.path.join(local_prefix, "lib"), exist_ok=True)

        # ── 1. Build Lua 5.4.7 from source ──
        lua_url = "https://www.lua.org/ftp/lua-5.4.7.tar.gz"
        lua_sha256 = (
            "9fbf5e28ef86c69858f6d3d34eccc32e911c1a28b4120ff3e84aaa70cfbf1e30"
        )
        lua_archive = os.path.join(build_dir, "lua-5.4.7.tar.gz")
        self._download(lua_url, lua_archive)
        self._verify_sha256(lua_archive, lua_sha256)
        self.run(f'tar xzf "{lua_archive}" -C "{build_dir}"')
        lua_src = os.path.join(build_dir, "lua-5.4.7")

        # Build lua with make linux target (HarmonyOS is Linux-like)
        self.run(
            f'make -C "{lua_src}" linux '
            f'MYCFLAGS="-fPIC" CC={cc} LD="{cc}" '
            f'AR="{ar} rcu" RANLIB={ranlib} '
            f'LDFLAGS="{ld_flag}"',
            cwd=lua_src,
        )

        # Install lua to local prefix
        self.run(
            f'make -C "{lua_src}" install INSTALL_TOP="{local_prefix}"',
            cwd=lua_src,
        )

        # Sign lua binary on OHOS (R7: safety popup)
        if is_ohos:
            self._sign_elf(os.path.join(local_prefix, "bin", "lua"))
            self._sign_elf(os.path.join(local_prefix, "bin", "luac"))

        # ── 2. Build SQLite3 from amalgamation source ──
        sqlite_url = (
            "https://www.sqlite.org/2024/sqlite-autoconf-3460000.tar.gz"
        )
        sqlite_sha256 = (
            "6f8e6a7b335273748816f9b3b62bbdc372a889de8782d7f048c653a447417a7d"
        )
        sqlite_archive = os.path.join(build_dir, "sqlite-autoconf-3460000.tar.gz")
        self._download(sqlite_url, sqlite_archive)
        self._verify_sha256(sqlite_archive, sqlite_sha256)
        self.run(f'tar xzf "{sqlite_archive}" -C "{build_dir}"')
        sqlite_src = os.path.join(build_dir, "sqlite-autoconf-3460000")

        # Compile sqlite3 amalgamation directly (avoids configure issues on OHOS)
        self.run(
            f'{cc} -c -O2 -fPIC '
            f'-DSQLITE_THREADSAFE=1 -DSQLITE_ENABLE_FTS5 '
            f'"{sqlite_src}/sqlite3.c" -o "{sqlite_src}/sqlite3.o"',
            cwd=sqlite_src,
        )
        self.run(
            f'{ar} rcu "{sqlite_src}/libsqlite3.a" "{sqlite_src}/sqlite3.o"'
        )
        self.run(f'{ranlib} "{sqlite_src}/libsqlite3.a"')

        # Install sqlite3 to local prefix
        shutil.copy(
            os.path.join(sqlite_src, "sqlite3.h"),
            os.path.join(local_prefix, "include"),
        )
        shutil.copy(
            os.path.join(sqlite_src, "sqlite3ext.h"),
            os.path.join(local_prefix, "include"),
        )
        shutil.copy(
            os.path.join(sqlite_src, "libsqlite3.a"),
            os.path.join(local_prefix, "lib"),
        )

        # ── 3. Modify luasql config for local build environment ──
        config_path = os.path.join(src, "config")
        with open(config_path, "r") as f:
            config = f.read()

        config = config.replace(
            "PREFIX ?= /usr", f"PREFIX ?= {local_prefix}"
        )
        config = config.replace(
            "LUA_SYS_VER ?= 5.2", "LUA_SYS_VER ?= 5.4"
        )
        config = config.replace(
            "LUA_INC ?= $(PREFIX)/include/lua$(LUA_SYS_VER)",
            "LUA_INC ?= $(PREFIX)/include",
        )
        config = config.replace(
            "DRIVER_LIBS_sqlite3 ?= -L/opt/local/lib -lsqlite3",
            "DRIVER_LIBS_sqlite3 ?= -L$(PREFIX)/lib -lsqlite3 -llua -lm -ldl",
        )
        config = config.replace(
            "DRIVER_INCS_sqlite3 ?= -I/opt/local/include",
            "DRIVER_INCS_sqlite3 ?= -I$(PREFIX)/include",
        )
        config = config.replace("CC= gcc", f"CC= {cc}")

        with open(config_path, "w") as f:
            f.write(config)

        # ── 4. Build luasql sqlite3 driver ──
        self.run("make sqlite3", cwd=src)

        # Sign the .so on OHOS (needed for loading)
        if is_ohos:
            self._sign_elf(os.path.join(src, "src", "sqlite3.so"))

    def package(self):
        src = self.source_folder
        build_dir = self.build_folder
        local_prefix = os.path.join(build_dir, "local_install")

        # Copy luasql .so module
        lua_libdir = os.path.join(
            self.package_folder, "lib", "lua", "5.4", "luasql"
        )
        os.makedirs(lua_libdir, exist_ok=True)
        copy(self, "sqlite3.so", os.path.join(src, "src"), lua_libdir)

        # Copy lua binary (needed for testing)
        copy(
            self,
            "lua",
            os.path.join(local_prefix, "bin"),
            os.path.join(self.package_folder, "bin"),
        )

        # Copy lua headers and static lib (for downstream builds)
        copy(
            self,
            "*.h",
            os.path.join(local_prefix, "include"),
            os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "liblua.a",
            os.path.join(local_prefix, "lib"),
            os.path.join(self.package_folder, "lib"),
        )

    def package_info(self):
        self.cpp_info.libs = ["luasql"]
        self.cpp_info.libdirs = ["lib/lua/5.4/luasql"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
