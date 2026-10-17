#!/usr/bin/env python3
"""Conan recipe for aconf 0.8.1 — Alpine configuration management daemon (Lua scripts)."""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AconfConan(ConanFile):
    name = "aconf"
    version = "0.8.1"
    description = "aconf - Alpine configuration management daemon (Lua + shell)"
    license = "MIT"
    homepage = "https://gitlab.alpinelinux.org/alpinelinux/aconf"
    url = "https://gitlab.alpinelinux.org/alpinelinux/aconf"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # aconf 是 Lua 配置守护进程，运行时依赖 lua
        self.requires("lua/5.4.8")

    def layout(self):
        basic_layout(self)
        # aconf 是 in-source 构建（Makefile 在源码根目录，无 configure）
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # aconf 是 Lua/脚本项目，无 C 编译。Makefile 的 all 目标（doc/index.html）
        # 需要 ldoc（OHOS 环境无），预生成 doc 文件让 make 通过。
        doc = os.path.join(self.source_folder, "doc")
        os.makedirs(doc, exist_ok=True)
        for f in ("index.html", "ldoc.css"):
            p = os.path.join(doc, f)
            if not os.path.exists(p):
                open(p, "w").close()
        self.run("make -j1")

    def package(self):
        # make install 用 ROOT_DIR 指定安装前缀（Makefile 无 DESTDIR 支持）
        staging = os.path.join(self.package_folder, "staging")
        self.run(f"make install ROOT_DIR={staging}")
        usr = os.path.join(staging, "usr")
        if not os.path.isdir(usr):
            return
        import shutil
        # 1) usr/sbin/aconfd → package/bin/aconfd（标准 bin/ 目录，L1e 破坏性验证依赖）
        sbin = os.path.join(usr, "sbin")
        if os.path.isdir(sbin):
            os.makedirs(os.path.join(self.package_folder, "bin"), exist_ok=True)
            for f in os.listdir(sbin):
                shutil.copy2(
                    os.path.join(sbin, f),
                    os.path.join(self.package_folder, "bin", f),
                )
        # 2) usr/share/lua/5.3/aconf → package/usr/share/lua/5.4/aconf（制品仓 lua 为 5.4.8）
        lua53 = os.path.join(usr, "share", "lua", "5.3", "aconf")
        if os.path.isdir(lua53):
            shutil.copytree(
                lua53,
                os.path.join(self.package_folder, "usr", "share", "lua", "5.4", "aconf"),
            )
        # 3) usr/share/aconf/{augeas,web,server.lua,LICENSE} → package/usr/share/aconf/
        #    跳过运行时软链接 aconf/config（指向系统 /usr/share/lua 与 /etc/aconf）
        aconf_share = os.path.join(usr, "share", "aconf")
        if os.path.isdir(aconf_share):
            pkg_aconf = os.path.join(self.package_folder, "usr", "share", "aconf")
            for item in os.listdir(aconf_share):
                s = os.path.join(aconf_share, item)
                if os.path.islink(s) or not os.path.exists(s):
                    continue  # 跳过运行时软链接与断链
                d = os.path.join(pkg_aconf, item)
                os.makedirs(os.path.dirname(d), exist_ok=True)
                if os.path.isdir(s):
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
        # 清理 staging 临时安装树（避免残留绝对软链接与 5.3 路径副本）
        if os.path.isdir(staging):
            shutil.rmtree(staging)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
