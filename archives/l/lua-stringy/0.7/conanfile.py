#!/usr/bin/env python3
"""Conan recipe for lua-stringy 0.7 — Fast string operations for Lua.

lua-stringy provides C-accelerated string methods (split, strip, find,
join, count, startswith, endswith) for Lua.

Build approach:
  - lua/5.4.8 (conan) provides liblua.a (compiled with -fPIC) and headers
  - A Lua interpreter is built from source (lua.c) against the conan
    liblua.a, since lua/5.4.8 conan package does not ship a binary
  - stringy.so is compiled and linked against the conan liblua.a
  - The lua binary is packaged for use by test_package
"""
import os
import shutil
import hashlib
from pathlib import Path

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LuaStringyConan(ConanFile):
    name = "lua-stringy"
    version = "0.7"
    description = (
        "C extension for fast string methods "
        "(split, strip, find, join, count, startswith, endswith)"
    )
    license = "MIT/X11"
    homepage = "https://github.com/mdeneen/lua-stringy"

    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lua/5.4.8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── helpers ──────────────────────────────────────────

    def _get_cc(self):
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return comp_execs.get("c") or "clang"

    def _is_ohos(self):
        return self.settings.os == "OHOS"

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
        """Download a file using curl."""
        self.run(f'curl -L -sS --fail -o "{dest}" "{url}"')

    def _verify_sha256(self, path, expected):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        actual = h.hexdigest()
        if actual != expected:
            raise RuntimeError(
                f"SHA256 mismatch: expected {expected}, got {actual}"
            )

    # ── build ────────────────────────────────────────────

    def build(self):
        apply_conandata_patches(self)

        cc = self._get_cc()
        is_ohos = self._is_ohos()

        # conan-provided lua headers and liblua.a (compiled with -fPIC)
        lua_dep = self.dependencies["lua"]
        lua_inc = os.path.join(lua_dep.package_folder, "include")
        lua_lib = os.path.join(lua_dep.package_folder, "lib")

        build_dir = self.build_folder
        local_bin = os.path.join(build_dir, "bin")
        os.makedirs(local_bin, exist_ok=True)

        # ── 1. Build Lua interpreter from source ──
        # lua/5.4.8 conan package only ships liblua.a (no interpreter binary).
        # Download lua source, extract lua.c, compile and link against
        # the conan-provided liblua.a.
        lua_url = "https://www.lua.org/ftp/lua-5.4.8.tar.gz"
        lua_sha256 = (
            "4f18ddae154e793e46eeab727c59ef1c0c0c2b744e7b94219710d76f530629ae"
        )
        lua_archive = os.path.join(build_dir, "lua-5.4.8.tar.gz")
        self._download(lua_url, lua_archive)
        self._verify_sha256(lua_archive, lua_sha256)
        # Extract only lua.c from the tarball
        self.run(
            f'tar xzf "{lua_archive}" '
            f'-C "{build_dir}" lua-5.4.8/src/lua.c'
        )
        lua_c_src = os.path.join(build_dir, "lua-5.4.8", "src", "lua.c")

        # Build lua interpreter linked against conan liblua.a
        self.run(
            f'{cc} -o "{local_bin}/lua" "{lua_c_src}" '
            f'-I"{lua_inc}" -L"{lua_lib}" -llua -lm -ldl '
            f'-Wl,-rpath,"{lua_lib}"'
        )
        if is_ohos:
            self._sign_elf(os.path.join(local_bin, "lua"))

        # ── 2. Build stringy.so ──
        # Source files are in the stringy/ subdirectory (v0.7-0 tag layout)
        stringy_src = os.path.join(self.source_folder, "stringy")
        cflags = "-O3 -Wall -Werror -fPIC"

        self.run(
            f'{cc} -c {cflags} -I"{lua_inc}" '
            f'-o stringy.o "{stringy_src}/stringy.c"'
        )
        self.run(
            f'{cc} -shared stringy.o '
            f'-L"{lua_lib}" -llua -lm -ldl -o stringy.so'
        )
        if is_ohos:
            self._sign_elf(os.path.join(build_dir, "stringy.so"))

    # ── package ──────────────────────────────────────────

    def package(self):
        lua_ver = "5.4"

        # Copy stringy.so to lib/lua/5.4/
        lua_libdir = os.path.join(
            self.package_folder, "lib", "lua", lua_ver
        )
        os.makedirs(lua_libdir, exist_ok=True)
        copy(self, "stringy.so", self.build_folder, lua_libdir)

        # Copy lua binary (needed for test_package)
        local_bin = os.path.join(self.build_folder, "bin")
        copy(
            self,
            "lua",
            local_bin,
            os.path.join(self.package_folder, "bin"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        lua_ver = "5.4"
        pkg = self.package_folder
        # Expose Lua module search path for downstream consumers
        self.runenv_info.define(
            "LUA_CPATH",
            os.path.join(pkg, "lib", "lua", lua_ver, "?.so") + ";;",
        )
