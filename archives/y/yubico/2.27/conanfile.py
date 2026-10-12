#!/usr/bin/env python3
"""Yubico PAM 模块（pam_yubico / yubico-pam）2.27 的 Conan 配方。

- 构建系统: autotools（官方 release 源树含预生成 configure，免 automake）
- 依赖: linux-pam/1.7.2（security/pam_*.h + libpam.so）、json-c/0.18（注意 0.18，
  不是 0.17——ykpers 依赖 0.18，用 0.17 会版本冲突）、ykclient/2.15（静态 .a）、
  ykpers/1.20.0（静态 .a，含 libusb-1.0.a）
- 产物: lib/security/pam_yubico.so（PAM 模块）+ bin/ykpamcfg（CLI 工具，R38）
- 平台要点（与本地探索构建一致的验证结论）:
  1) tarball 自带 config.guess(2018)/config.sub 不识别 OHOS → 补丁加
     aarch64:OHOS/HarmonyOS + linux-ohos* 识别（见 patches/）
  2) configure 内 config.status 硬编码 `umask 077 && mktemp -d` 建 0700 临时
     目录，OHOS 沙箱上所有者亦不可写（librrd 先例）→ 补丁 umask 077→022
  3) ykclient/yubikey 为静态库，AC_LIB_HAVE_LINKFLAGS 链接探测失败 →
     configure_args 传 ac_cv_libykclient=yes ac_cv_libyubikey=yes 跳过探测，
     并在 LIBS 注入传递依赖（-ljson-c -lcurl -lusb-1.0）
  4) ykpers-1.pc 的 prefix 烘焙为构建期 staging 路径（不存在）→ 显式传
     YKPERS_CFLAGS/YKPERS_LIBS 指向 conan 包真实路径
  5) 依赖包 lib/*.la 烘焙构建期路径 → build() 开头改名 *.la.bak 使 libtool
     回退 -L+-l 解析真实 .a/.so（ideviceinstaller #6853 先例）
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class YubicoConan(ConanFile):
    name = "yubico"
    version = "2.27"
    description = "Yubico PAM module (pam_yubico, yubico-pam) - YubiKey OTP authentication for PAM"
    license = "BSD-2-Clause"
    homepage = "https://developers.yubico.com/yubico-pam/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("linux-pam/1.7.2", transitive_headers=True, transitive_libs=True)
        self.requires("json-c/0.18")
        self.requires("ykclient/2.15")
        self.requires("ykpers/1.20.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)

        # 静态库链接探测无法自动解析传递依赖 → 缓存变量覆盖（见模块 docstring）
        tc.configure_args.append("ac_cv_libykclient=yes")
        tc.configure_args.append("ac_cv_libyubikey=yes")

        # ykpers-1.pc 的 prefix 指向构建期 staging 路径（不存在）→ 显式覆盖
        ykpers = self.dependencies["ykpers"].package_folder
        tc.configure_args.append(f"YKPERS_CFLAGS=-I{ykpers}/include/ykpers-1")
        tc.configure_args.append(f"YKPERS_LIBS=-L{ykpers}/lib -lykpers-1 -lusb-1.0")

        # 依赖注入（含传递依赖，如 ykclient→curl）：静态库链接需要全部 -L/-I
        # 与运行期 LD_LIBRARY_PATH（conftest 链接后还要执行验证）
        include_dirs, lib_dirs = [], []
        for dep in self.dependencies.values():
            if dep.package_folder is None:
                continue
            inc = os.path.join(dep.package_folder, "include")
            lib = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(inc):
                include_dirs.append(inc)
            if os.path.isdir(lib):
                lib_dirs.append(lib)
        env = Environment()
        env.append("CPPFLAGS", " ".join(f"-I{i}" for i in include_dirs))
        env.append("LDFLAGS", " ".join(f"-L{l}" for l in lib_dirs))
        env.define("LIBS", "-ljson-c -lcurl -lusb-1.0")
        env.append("LD_LIBRARY_PATH", ":".join(lib_dirs))
        env.vars(self).save_script("conanbuild_env")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # 消费者侧禁用依赖包 libtool *.la 包装：依赖包 .la 内烘焙构建期路径，
        # libtool 优先解析 .la 报 "cannot find the library '...staging/lib/*.la'"
        # （ideviceinstaller #6853 先例）。改名 *.la.bak 回退 -L+-l 解析真实库。
        for dep in self.dependencies.values():
            if dep.package_folder is None:
                continue
            dep_lib = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(dep_lib):
                continue
            for entry in os.listdir(dep_lib):
                if entry.endswith(".la"):
                    os.rename(os.path.join(dep_lib, entry),
                              os.path.join(dep_lib, entry + ".bak"))

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # PAM 模块（lib/security/pam_yubico.so）由 PAM 运行时加载，非消费者
        # 链接库；ykpamcfg 为独立 CLI 工具（已声明 commands.json，R38）
        self.cpp_info.libs = []
