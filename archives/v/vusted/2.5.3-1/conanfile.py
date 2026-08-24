#!/usr/bin/env python3
"""Conan recipe for vusted 2.5.3-1."""

import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class VustedConan(ConanFile):
    name = "vusted"
    version = "2.5.3-1"
    description = "Busted wrapper for testing Neovim plugins"
    license = "MIT"
    homepage = "https://github.com/notomo/vusted"
    url = "https://github.com/notomo/vusted"

    exports_sources = "compat/*", "compat/system/*", "compat/term/*"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("luasystem/0.6.3-1")
        self.requires("busted/2.2.0-1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        lua_share = os.path.join(self.package_folder, "share", "lua", "5.4")
        copy(self, "*.lua", src=os.path.join(self.source_folder, "lua", "vusted"), dst=os.path.join(lua_share, "vusted"))
        copy(
            self,
            "*.lua",
            src=os.path.join(self.source_folder, "lua", "busted", "outputHandlers", "vusted"),
            dst=os.path.join(lua_share, "busted", "outputHandlers", "vusted"),
        )
        compat = os.path.join(self.export_sources_folder, "compat")
        copy(self, "lfs.lua", src=compat, dst=lua_share)
        copy(self, "init.lua", src=os.path.join(compat, "system"), dst=os.path.join(lua_share, "system"))
        copy(self, "init.lua", src=os.path.join(compat, "term"), dst=os.path.join(lua_share, "term"))
        copy(self, "colors.lua", src=os.path.join(compat, "term"), dst=os.path.join(lua_share, "term"))
        copy(self, "vusted", src=os.path.join(self.source_folder, "bin"), dst=os.path.join(self.package_folder, "bin"))
        copy(self, "vusted_entry.vim", src=os.path.join(self.source_folder, "bin"), dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

        self._patch_run_lua(os.path.join(lua_share, "vusted", "run.lua"))
        self._patch_entry_vim(os.path.join(self.package_folder, "bin", "vusted_entry.vim"))
        command = os.path.join(self.package_folder, "bin", "vusted")
        if os.path.exists(command):
            os.chmod(command, 0o755)

    def _patch_run_lua(self, path):
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
        old = (
            "local version = _VERSION:sub(5)\n"
            "    local package_version = vim.fn.system(\"luarocks --lua-version=\" .. version .. \" show vusted --mversion\")\n"
            "    print(package_version)"
        )
        new = "print('2.5.3')"
        text = text.replace(old, new)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)

    def _patch_entry_vim(self, path):
        replacement = """let s:this_path = expand('<sfile>')
let s:root_path = fnamemodify(s:this_path, ':h:h')
if isdirectory(s:root_path .. '/spec')
    \" HACK: for installation by clone
    let &runtimepath = s:root_path .. ',' .. &runtimepath
endif

try
lua <<EOF
    local lua_path = os.getenv('LUA_PATH')
    if lua_path and lua_path ~= '' then
      package.path = package.path .. ';' .. lua_path
    end
    local lua_cpath = os.getenv('LUA_CPATH')
    if lua_cpath and lua_cpath ~= '' then
      package.cpath = package.cpath .. ';' .. lua_cpath
    end
    require('vusted/run')()
EOF
catch
    $ put =v:throwpoint
    $ put =v:exception
    1delete _
    %print
    cquit
endtry
"""
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(replacement)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        lua_share = os.path.join(self.package_folder, "share", "lua", "5.4")
        bin_dir = os.path.join(self.package_folder, "bin")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", bin_dir)
        self.runenv_info.define(
            "LUA_PATH",
            os.path.join(lua_share, "?.lua") + ";" + os.path.join(lua_share, "?", "init.lua") + ";;",
        )

