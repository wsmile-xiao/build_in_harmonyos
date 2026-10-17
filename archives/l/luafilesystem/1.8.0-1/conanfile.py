#!/usr/bin/env python3
"""Conan recipe for luafilesystem 1.8.0-1."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class LuaFileSystemConan(ConanFile):
    name = "luafilesystem"
    version = "1.8.0-1"
    description = "File system library for the Lua programming language"
    license = "MIT/X11"
    homepage = "https://github.com/lunarmodules/luafilesystem"
    url = "https://github.com/lunarmodules/luafilesystem"
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} is not supported")

    def requirements(self):
        self.requires("lua/5.4.8.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        lua = self.dependencies["lua"].cpp_info
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "cc")
        source = os.path.join(self.source_folder, "src", "lfs.c")
        obj = os.path.join(self.build_folder, "lfs.o")
        output = os.path.join(self.build_folder, "lfs.so")

        cflags = ["-O2", "-fPIC", "-Wall", "-Wextra"]
        for include in lua.includedirs:
            cflags.append(f'-I"{include}"')
        self.run(f'"{cc}" -c "{source}" -o "{obj}" ' + " ".join(cflags))

        libdirs = " ".join(f'-L"{path}"' for path in lua.libdirs)
        libs = " ".join(f"-l{name}" for name in lua.libs)
        system_libs = " ".join(f"-l{name}" for name in lua.system_libs)
        self.run(f'"{cc}" -shared -fPIC -o "{output}" "{obj}" {libdirs} {libs} {system_libs}')
        self._run_adapted_upstream_test()

    def _lua_executable(self):
        lua = self.dependencies["lua"].cpp_info
        if lua.bindirs:
            candidate = os.path.join(lua.bindirs[0], "lua")
            if os.path.exists(candidate):
                return candidate
        return "lua"

    def _run_adapted_upstream_test(self):
        source_test = os.path.join(self.source_folder, "tests", "test.lua")
        work = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(work, exist_ok=True)
        adapted_test = os.path.join(work, "test.lua")
        shutil.copy2(source_test, adapted_test)
        self._adapt_upstream_test(adapted_test)

        env = Environment()
        env.define("TMPDIR", work)
        env.define("LUA_CPATH", os.path.join(self.build_folder, "?.so") + ";;")
        with env.vars(self).apply():
            self.run(f'"{self._lua_executable()}" "test.lua"', cwd=work)

    def _adapt_upstream_test(self, test_file):
        with open(test_file, "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()

        text = "\n".join(lines)
        tmp_marker = 'local tmp = "/tmp"'
        if tmp_marker not in text:
            raise ConanException("upstream test.lua no longer contains expected /tmp marker")
        text = text.replace(tmp_marker, 'local tmp = os.getenv("TMPDIR") or "/tmp"', 1)
        lines = text.splitlines()

        start_marker = 'assert (lfs.link (tmpfile, "_a_hard_link_for_test_"))'
        end_marker = 'assert (os.remove"_a_hard_link_for_test_")'
        try:
            start = next(i for i, line in enumerate(lines) if line.strip() == start_marker)
            end = next(i for i, line in enumerate(lines) if line.strip() == end_marker)
        except StopIteration as exc:
            raise ConanException("upstream test.lua hardlink block no longer matches expected shape") from exc
        if start >= end:
            raise ConanException("upstream test.lua hardlink block has invalid bounds")

        replacement = [
            '  local hardlink_ok, hardlink_err = lfs.link (tmpfile, "_a_hard_link_for_test_")',
            "  if hardlink_ok then",
            '    assert (lfs.symlinkattributes"_a_hard_link_for_test_".mode == "file")',
            '  elseif tostring(hardlink_err):match("Operation not permitted") or tostring(hardlink_err):match("Permission denied") then',
            '    io.write("[hardlink skipped: "..tostring(hardlink_err).."]")',
            "  else",
            '    error(hardlink_err or "hardlink creation failed")',
            "  end",
            "",
            "  local fd = io.open(tmpfile)",
            '  assert(fd:read("*a") == data)',
            "  fd:close()",
            "",
            '  fd = io.open("_a_link_for_test_")',
            '  assert(fd:read("*a") == data)',
            "  fd:close()",
            "",
            "  if hardlink_ok then",
            '    fd = io.open("_a_hard_link_for_test_")',
            '    assert(fd:read("*a") == data)',
            "    fd:close()",
            "",
            '    fd = io.open("_a_hard_link_for_test_", "w+")',
            '    local data2 = "write in hard link"',
            "    fd:write(data2)",
            "    fd:close()",
            "",
            "    fd = io.open(tmpfile)",
            '    assert(fd:read("*a") == data2)',
            "    fd:close()",
            "",
            "    if is_unix then",
            '      assert (lfs.attributes (tmpfile, "nlink") == 2)',
            "    end",
            "  end",
            "",
            '  assert (os.remove"_a_link_for_test_")',
            "  if hardlink_ok then",
            '    assert (os.remove"_a_hard_link_for_test_")',
            "  end",
        ]
        lines[start : end + 1] = replacement
        with open(test_file, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines) + "\n")

    def package(self):
        copy(self, "lfs.so", src=self.build_folder, dst=os.path.join(self.package_folder, "lib", "lua", "5.4"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        lua_lib = os.path.join(self.package_folder, "lib", "lua", "5.4")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.define("LUA_CPATH", os.path.join(lua_lib, "?.so") + ";;")
