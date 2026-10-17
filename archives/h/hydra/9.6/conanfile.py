#!/usr/bin/env python3
"""Conan recipe — hydra 9.6 (THC Hydra) for HarmonyOS PC aarch64.

Adaptation notes:
- hydra 使用自定义 configure 脚本（非标准 autotools，无 configure.ac），
  检测各可选库后生成 Makefile（Makefile.unix + Makefile.in + Makefile.am）。
- 产物是可执行文件 hydra + pw-inspector，package_type 应为 application。
- 依赖：openssl（OHOS sysroot 无，使用制品仓 openssl/3.5.6）；zlib 等可选
  库在 OHOS sysroot 可用时由 configure 自动检测；GTK GUI（xhydra）禁用。
- configure 在 OHOS 上需处理 umask 077 / config 探测等平台差异。
"""
from conan import ConanFile
from conan.tools.files import (
    get, apply_conandata_patches, export_conandata_patches,
    load, save, copy,
)
from conan.tools.layout import basic_layout
import os
import shutil


class HydraConan(ConanFile):
    name = "hydra"
    version = "9.6"
    description = "THC Hydra - 快速网络登录破解工具，支持 50+ 协议"
    license = "MIT"
    homepage = "https://github.com/vanhauser-thc/thc-hydra"
    url = "https://github.com/vanhauser-thc/thc-hydra"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # OHOS umask 077 兼容：configure 生成 Makefile.in 时可能因目录权限
        # 失败，先统一为 umask 022。
        configure = os.path.join(src, "configure")
        if os.path.isfile(configure):
            content = load(self, configure)
            content = content.replace("umask 077", "umask 022")
            save(self, configure, content)

        openssl_root = self.dependencies["openssl"].package_folder
        args = [
            "./configure",
            "--prefix=" + self.package_folder,
            "--disable-xhydra",          # 无 GTK GUI
            "--nostrip",                 # 保留符号便于 test
        ]
        if openssl_root:
            args.append("--with-ssl=" + os.path.join(openssl_root, "include", "openssl"))
            args.append("--with-ssl-lib=" + os.path.join(openssl_root, "lib"))
        self.run(
            "cd {src} && {args}".format(src=src, args=" ".join(args)),
            env=["CONFIG_SHELL=/data/service/hnp/bin/bash"],
        )
        self.run("cd {src} && make -j1".format(src=src))

    def package(self):
        src = self.source_folder
        # 手动安装（hydra 的 install 目标依赖 strip 与 /etc 路径，DESTDIR 安装
        # 在 OHOS 上不稳妥，直接拷贝产物）。
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        for name in ("hydra", "pw-inspector", "hydra-wizard.sh", "dpl4hydra.sh"):
            f = os.path.join(src, name)
            if os.path.isfile(f):
                shutil.copyfile(f, os.path.join(bin_dir, name))
                # 显式赋予可执行权限（shutil.copyfile 不保留源文件权限位，
                # 缺执行位会导致 test_package 运行 hydra 时报 Error 126）
                os.chmod(os.path.join(bin_dir, name), 0o755)
        # 文档
        copy(self, "README", src=src, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE", src=src, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.system_libs = []
