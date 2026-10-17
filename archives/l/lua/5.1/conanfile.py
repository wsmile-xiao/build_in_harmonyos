#!/usr/bin/env python3
import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LuaConan(ConanFile):
    name = "lua"
    version = "5.1"
    description = "Lightweight embeddable scripting language"
    license = "MIT"
    homepage = "https://www.lua.org/"
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_tools(self):
        tools = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = tools.get("c", "clang")
        return {
            "cc": cc,
            "ar": tools.get("ar") or self._tool_next_to_compiler(cc, "llvm-ar"),
            "ranlib": tools.get("ranlib") or self._tool_next_to_compiler(cc, "llvm-ranlib"),
        }

    def _tool_next_to_compiler(self, compiler, tool):
        if compiler and os.path.isabs(compiler):
            candidate = os.path.join(os.path.dirname(compiler), tool)
            if os.path.exists(candidate):
                return candidate
        try:
            resolved = subprocess.check_output(
                [compiler, f"--print-prog-name={tool}"], text=True
            ).strip()
            if resolved:
                return resolved
        except (OSError, subprocess.SubprocessError):
            pass
        return tool

    def _link_env(self):
        env = Environment()
        if self.settings.os == "OHOS":
            sdk_root = "/data/service/hnp/ohos-sdk.org"
            if os.path.isdir(sdk_root):
                for entry in sorted(os.listdir(sdk_root), reverse=True):
                    llvm_lib = os.path.join(sdk_root, entry, "ohos", "native", "llvm", "lib")
                    if os.path.isdir(llvm_lib):
                        env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
                        break
        return env

    def build(self):
        apply_conandata_patches(self)
        tools = self._compiler_tools()
        link_env = self._link_env()
        src = os.path.join(self.source_folder, "src")
        optimize = "-O2" if self.settings.build_type == "Release" else "-O0 -g"
        cflags = [
            optimize,
            "-Wall",
            "-fPIC",
            "-DLUA_USE_POSIX",
            "-DLUA_USE_DLOPEN",
        ]
        core_sources = [
            "lapi.c", "lcode.c", "ldebug.c", "ldo.c", "ldump.c", "lfunc.c",
            "lgc.c", "llex.c", "lmem.c", "lobject.c", "lopcodes.c",
            "lparser.c", "lstate.c", "lstring.c", "ltable.c", "ltm.c",
            "lundump.c", "lvm.c", "lzio.c",
        ]
        lib_sources = [
            "lauxlib.c", "lbaselib.c", "ldblib.c", "liolib.c", "lmathlib.c",
            "loslib.c", "ltablib.c", "lstrlib.c", "loadlib.c", "linit.c",
        ]
        objects = []
        for source in core_sources + lib_sources + ["lua.c", "luac.c", "print.c"]:
            obj = source[:-2] + ".o"
            self.run(
                " ".join(
                    [
                        shlex.quote(tools["cc"]),
                        "-c",
                        *cflags,
                        shlex.quote(source),
                        "-o",
                        shlex.quote(obj),
                    ]
                ),
                cwd=src,
            )
            objects.append(obj)

        lib_objects = [source[:-2] + ".o" for source in core_sources + lib_sources]
        self.run(
            " ".join(
                [
                    shlex.quote(tools["ar"]),
                    "rcu",
                    "liblua.a",
                    *[shlex.quote(obj) for obj in lib_objects],
                ]
            ),
            cwd=src,
        )
        self.run(f'{shlex.quote(tools["ranlib"])} liblua.a', cwd=src)
        with link_env.vars(self).apply():
            self.run(
                f'{shlex.quote(tools["cc"])} -o lua lua.o liblua.a -ldl -lm',
                cwd=src,
            )
            self.run(
                f'{shlex.quote(tools["cc"])} -o luac luac.o print.o liblua.a -ldl -lm',
                cwd=src,
            )
        self.run(f'"{os.path.join(src, "lua")}" "{os.path.join(self.source_folder, "test", "hello.lua")}"')

    def package(self):
        src = os.path.join(self.source_folder, "src")
        copy(self, "*.h", src=src, dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "lua.hpp", src=os.path.join(self.source_folder, "etc"), dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "liblua.a", src=src, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.1", src=os.path.join(self.source_folder, "doc"), dst=os.path.join(self.package_folder, "man", "man1"), keep_path=False)
        copy(self, "COPYRIGHT", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

        for relpath in ("include/lua.h", "lib/liblua.a"):
            path = os.path.join(self.package_folder, relpath)
            if not os.path.exists(path):
                raise RuntimeError(f"Expected Lua package artifact missing: {relpath}")

    def package_info(self):
        self.cpp_info.libs = ["lua"]
        self.cpp_info.system_libs = ["dl", "m"]
        self.cpp_info.defines = ["LUA_USE_POSIX", "LUA_USE_DLOPEN"]
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "lua")
        self.cpp_info.set_property("cmake_target_name", "lua::lua")
        self.cpp_info.set_property("pkg_config_name", "lua-5.1")
