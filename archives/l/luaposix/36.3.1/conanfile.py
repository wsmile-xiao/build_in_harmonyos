#!/usr/bin/env python3
"""Conan recipe — luaposix 36.3.1 (luke)"""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LuaposixConan(ConanFile):
    name = "luaposix"
    version = "36.3.1"
    description = "Lua bindings for POSIX APIs"
    license = "MIT"
    homepage = "https://github.com/luaposix/luaposix"
    # Lua C modules are always built as .so; shared-library avoids the
    # meaningless shared option (which would inflate package IDs).
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lua/5.5.0")

    def build_requirements(self):
        # luke is a Lua script; lua interpreter must be in build PATH (tool_requires auto-adds bindirs)
        self.tool_requires("lua/5.5.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # No-op: lua interpreter comes from tool_requires (auto PATH) and lua/5.5.0
        # package_info exports LUA_PATH/LUA_CPATH via runenv_info.
        pass

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # lua 同时是 host requires 与 build tool_requires，交叉编译时两上下文为
        # 不同实例，必须显式区分（否则 Conan 抛 multiple dependencies 异常）：
        #   - LUA_INCDIR/LUA_LIBDIR 指向 host（目标平台）的 lua 头文件/库
        #   - luke 解释器必须用 build（本机可执行）平台的 lua
        lua_host = self.dependencies.host["lua"]
        inc_dir = os.path.join(lua_host.package_folder, "include")
        lib_dir = os.path.join(lua_host.package_folder, "lib")
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "clang")
        # luaposix uses luke (build-aux/luke) as its build system.
        # R33: no bare shell env vars; resolve lua from tool_requires' package folder.
        luke = os.path.join(src, "build-aux", "luke")
        lua_build = self.dependencies.build["lua"]
        lua_exe = os.path.join(lua_build.package_folder, "bin", "lua")
        self._make_dir = src
        self.run(f"{lua_exe} {luke} PREFIX={src} LUA_INCDIR={inc_dir} LUA_LIBDIR={lib_dir} CC={cc}", env="conanbuild")

    def package(self):
        src = self.source_folder
        # luke outputs .so files under <src>/unix/posix/ (platform-specific dir)
        so_src = os.path.join(src, "unix", "posix")
        if not os.path.isdir(so_src):
            so_src = getattr(self, "_make_dir", src)
        copy(self, "*.so", src=so_src,
             dst=os.path.join(self.package_folder, "lib", "lua", "5.5", "posix"))
        # .lua files (incl. luke-generated version.lua) live in lib/posix/
        copy(self, "*.lua", src=os.path.join(src, "lib", "posix"),
             dst=os.path.join(self.package_folder, "share", "lua", "5.5", "posix"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        # Expose Lua module search paths for downstream consumers
        lua_ver = "5.5"
        pkg = self.package_folder
        self.runenv_info.define("LUA_CPATH",
                                os.path.join(pkg, "lib", "lua", lua_ver, "?.so") + ";;")
        self.runenv_info.define("LUA_PATH",
                                os.path.join(pkg, "share", "lua", lua_ver, "?.lua") + ";" +
                                os.path.join(pkg, "share", "lua", lua_ver, "?/init.lua") + ";;")
        self.cpp_info.set_property("cmake_file_name", "luaposix")
