#!/usr/bin/env python3
"""Conan recipe for luarocks5.5 3.13.0."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load, save
from conan.tools.layout import basic_layout


class Luarocks55Conan(ConanFile):
    name = "luarocks5.5"
    version = "3.13.0"
    description = "LuaRocks package manager configured for Lua 5.5"
    license = "MIT"
    homepage = "https://luarocks.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch"
    default_options = {"lua/*:with_tools": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lua/5.5.0")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("luarocks5.5 is supported only on Linux/OHOS")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        lua = self.dependencies["lua"]
        lua_root = str(lua.package_folder)
        lua_bin = os.path.join(lua_root, "bin")
        lua_exe = os.path.join(lua_bin, "lua")
        lua_include = os.path.join(lua_root, "include")
        lua_lib = os.path.join(lua_root, "lib")

        for path in (lua_exe, lua_include, lua_lib):
            if not os.path.exists(path):
                raise ConanException(f"Lua 5.5 dependency artifact missing: {path}")

        if cross_building(self):
            return

        configure = os.path.join(self.source_folder, "configure")
        os.chmod(configure, 0o755)
        configure_command = " ".join(
            [
                f'"{self._posix_path(configure)}"',
                "--prefix=/",
                "--sysconfdir=/etc",
                "--force-config",
                "--lua-version=5.5",
                f'--with-lua-bin="{self._posix_path(lua_bin)}"',
                f'--with-lua-include="{self._posix_path(lua_include)}"',
                f'--with-lua-lib="{self._posix_path(lua_lib)}"',
            ]
        )
        if os.name == "nt":
            self.run(f'"{self._configure_shell()}" {configure_command}', cwd=self.source_folder)
        else:
            self.run(configure_command, cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        if cross_building(self):
            self._package_cross()
            return

        self.run(f'make install DESTDIR="{self.package_folder}"', cwd=self.source_folder)

        for command in ("luarocks", "luarocks-admin"):
            script = os.path.join(self.package_folder, "bin", command)
            if not os.path.exists(script):
                raise ConanException(f"expected command was not installed: {script}")
            self._make_script_relocatable(script)
            os.chmod(script, 0o755)
        self._patch_portable_tmpname()

        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

    def _package_cross(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        for command in ("luarocks", "luarocks-admin"):
            src = os.path.join(self.source_folder, "src", "bin", command)
            dst = os.path.join(bin_dir, command)
            shutil.copyfile(src, dst)
            self._make_script_relocatable(dst)
            os.chmod(dst, 0o755)

        lua_module_dir = os.path.join(self.package_folder, "share", "lua", "5.5", "luarocks")
        copied = copy(self, "*.lua", os.path.join(self.source_folder, "src", "luarocks"), lua_module_dir)
        if not copied:
            raise ConanException("package() did not copy LuaRocks Lua modules")
        self._patch_portable_tmpname()

        config_dir = os.path.join(self.package_folder, "etc", "luarocks")
        save(
            self,
            os.path.join(config_dir, "config-5.5.lua"),
            """-- LuaRocks configuration

rocks_trees = {
   { name = "user", root = home .. "/.luarocks" };
   { name = "system", root = "/" };
}
variables = {
   LUA_VERSION = "5.5";
}
""",
        )

        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def _make_script_relocatable(self, script):
        with open(script, "r", encoding="utf-8") as handle:
            content = handle.read()
        marker = "local lr_prefix = "
        if marker in content:
            return

        lines = content.splitlines()
        if not lines or not lines[0].startswith("#!"):
            raise ConanException(f"unexpected LuaRocks launcher format: {script}")

        bootstrap = [
            lines[0],
            'local lr_bin = arg and arg[0] or ""',
            'local lr_prefix = lr_bin:gsub("[/\\\\][^/\\\\]+$", ""):gsub("[/\\\\]bin$", "")',
            'package.loaded["luarocks.core.hardcoded"] = { FORCE_CONFIG = true, SYSCONFDIR = lr_prefix .. "/etc/luarocks" }',
            'package.path = lr_prefix .. "/share/lua/5.5/?.lua;" .. package.path',
            'local list = package.searchers or package.loaders; table.insert(list, 1, function(name) if name:match("^luarocks%.") then local path = lr_prefix .. "/share/lua/5.5/" .. name:gsub("%.", "/") .. ".lua"; local loader, err = loadfile(path); if loader then return loader end; return err end end)',
        ]
        body = []
        for line in lines[1:]:
            compact = "".join(line.split())
            if line.startswith('package.loaded["luarocks.core.hardcoded"]'):
                continue
            if compact.startswith("package.path="):
                continue
            if line.startswith("local list = package.searchers"):
                continue
            body.append(line)
        with open(script, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(bootstrap + body) + "\n")

    def _patch_portable_tmpname(self):
        util_lua = os.path.join(
            self.package_folder,
            "share",
            "lua",
            "5.5",
            "luarocks",
            "core",
            "util.lua",
        )
        if not os.path.exists(util_lua):
            raise ConanException(f"expected LuaRocks utility module was not packaged: {util_lua}")
        content = load(self, util_lua)
        marker = "Conan OHOS portable tmpname fallback"
        if marker in content:
            return
        old = '''function util.popen_read(cmd, spec)
   local tmpfile = (dir_sep == "\\\\") and
   (os.getenv("TMP") .. "/luarocks-" .. tostring(math.floor(math.random() * 10000))) or
   os.tmpname()
   os.execute(cmd .. " > " .. tmpfile)
'''
        new = f'''function util.popen_read(cmd, spec)
   -- {marker}: os.tmpname() may fail on OHOS workers, so prefer
   -- an explicit writable temp directory before falling back to os.tmpname().
   local tmpdir = os.getenv("TMPDIR") or os.getenv("TMP") or os.getenv("TEMP")
   local tmpfile = tmpdir and
      (tmpdir .. dir_sep .. "luarocks-" .. tostring(os.time()) .. "-" .. tostring(math.floor(math.random() * 1000000))) or
      os.tmpname()
   os.execute(cmd .. " > " .. tmpfile)
'''
        if old not in content:
            raise ConanException("LuaRocks util.popen_read tmpname anchor not found")
        save(self, util_lua, content.replace(old, new))

    def _configure_shell(self):
        candidates = [
            os.environ.get("CONFIG_SHELL"),
            shutil.which("sh"),
            "C:/Program Files/Git/bin/sh.exe",
            "C:/Program Files/Git/usr/bin/sh.exe",
            "E:/Git/bin/sh.exe",
            "E:/Git/usr/bin/sh.exe",
        ]
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return self._posix_path(candidate)
        raise ConanInvalidConfiguration("A POSIX sh executable is required to run LuaRocks configure")

    def _posix_path(self, path):
        return str(path).replace("\\", "/")
