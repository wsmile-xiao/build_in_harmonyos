#!/usr/bin/env python3
"""Conan recipe — lmod 9.2.5 (Autotools)"""

import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class LmodConan(ConanFile):
    name = "lmod"
    version = "9.2.5"
    description = "Lua-based environment module system for dynamically managing user environment"
    license = "MIT"
    homepage = "https://github.com/TACC/Lmod"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lua/5.5.0")
        # lmod configure 会检查 posix 模块；luaposix 已合并到 main
        self.requires("luaposix/36.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Point lmod to the Lua installation from the Conan dependency
        lua_host = self.dependencies["lua"].package_folder
        lua_bin = os.path.join(lua_host, "bin")
        lua_exe = os.path.join(lua_bin, "lua")
        tc.configure_args.append(f"--with-lua={lua_exe}")
        tc.configure_args.append(f"--with-luac={lua_bin}/luac")
        tc.configure_args.append(f"--with-lua-include={lua_host}/include")
        tc.configure_args.append(f"--with-lua-lib={lua_host}/lib")
        # Fix cross-compilation: specify exact lua version so configure
        # doesn't need to execute the target binary to detect it.
        tc.configure_args.append("--with-lua-version=5.5.0")
        # Disable TCL support (tclsh not available on OHOS CI workers)
        tc.configure_args.append("--with-tcl=no")
        tc.configure_args.append("--with-fastTCLInterp=no")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # lmod configure 强制要求 tclsh，在 PATH 中创建假的 tclsh 绕过
        import os
        fake = os.path.join(os.getcwd(), "tclsh")
        with open(fake, "w") as f:
            f.write("#!/bin/sh\nexit 0\n")
        os.chmod(fake, 0o755)
        lua_host = self.dependencies["lua"].package_folder
        lua_bin = os.path.join(lua_host, "bin")
        os.environ["PATH"] = os.getcwd() + ":" + lua_bin + ":" + os.environ.get("PATH", "")
        # lmod configure 会检查 posix 模块；设置 LUA_CPATH/LUA_PATH 指向 luaposix 的安装路径
        lpkg = self.dependencies["luaposix"].package_folder
        lua_ver = "5.5"
        os.environ["LUA_CPATH"] = os.path.join(lpkg, "lib", "lua", lua_ver, "?.so") + ";;"
        os.environ["LUA_PATH"] = os.path.join(lpkg, "share", "lua", lua_ver, "?.lua") + ";" + \
                                 os.path.join(lpkg, "share", "lua", lua_ver, "?/init.lua") + ";;"
        # OHOS /tmp 只读导致 config.status 无法创建临时文件；
        # TMPDIR 指向 build 目录子目录（避免硬编码开发机路径）
        os.environ["TMPDIR"] = os.path.join(self.build_folder, "tmp")
        os.makedirs(os.environ["TMPDIR"], exist_ok=True)
        # 手动运行 configure（绕过 Autotools 封装）
        import subprocess
        src = self.source_folder
        build = self.build_folder
        # 手动运行 configure（--no-create 不执行 config.status）
        pkg = self.package_folder
        # lmod 的 Makefile 将 PKG 设为 {prefix}/lmod/{version}，
        # 所以 prefix 只需指向 {pkg}，PKG 自动变为 {pkg}/lmod/9.2.5
        # 参数与 generate() 的 AutotoolsToolchain 保持一致（AI 审计 P2）
        cfg_cmd = (f"cd {build} && {src}/configure --prefix={pkg} "
                   f"--with-lua={os.path.join(lua_bin, 'lua')} "
                   f"--with-luac={lua_bin}/luac "
                   f"--with-lua-include={lua_host}/include "
                   f"--with-lua-lib={lua_host}/lib "
                   f"--with-lua-version=5.5.0 "
                   f"--with-tcl=no "
                   f"--with-fastTCLInterp=no --no-create")
        subprocess.run(cfg_cmd, shell=True, check=True, env=os.environ)
        # 修改 config.status：用 mkdir -p 替换 mktemp -d（mktemp 在 tmpfs 上 Permission denied）
        cfg_st = os.path.join(build, "config.status")
        if os.path.exists(cfg_st):
            with open(cfg_st) as f:
                content = f.read()
            # 替换 mktemp -d 创建临时目录的部分
            old_line = 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`'
            new_line = f'tmp="{build}/lmod_conf_tmp"; mkdir -p "$tmp"; chmod 755 "$tmp"'
            content = content.replace(old_line, new_line)
            with open(cfg_st, "w") as f:
                f.write(content)
            os.chmod(cfg_st, 0o755)
        # 手动执行 config.status
        subprocess.run(f"cd {build} && ./config.status", shell=True, check=True, env=os.environ)
        # 运行 make
        subprocess.run(f"cd {build} && make -j1", shell=True, check=True, env=os.environ)

    def package(self):
        import subprocess
        build = self.build_folder
        pkg = self.package_folder
        # 手动运行 make install（prefix 已在 configure 时设定）
        subprocess.run(f"cd {build} && make install", shell=True, check=True, env=os.environ)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # 文件安装到 {package_folder}/lmod/9.2.5/ 下（--prefix 在 configure 时设定）
        pkg = self.package_folder
        self.runenv_info.define("LMOD_PKG", pkg)
        self.runenv_info.define("LMOD_DIR", os.path.join(pkg, "lmod", self.version))
        self.runenv_info.define("LMOD_VERSION", self.version)
