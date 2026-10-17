#!/usr/bin/env python3
"""Conan recipe for cjose 0.6.2.7 - C JOSE (JWS/JWE/JWK) implementation for HarmonyOS PC (aarch64).

构建系统：autotools (configure/make)，in-tree 构建 (basic_layout)。

适配要点：
- config.guess 不识别 HarmonyOS/HongMeng 内核 → 显式 --build/--host
  aarch64-unknown-linux-ohos 三元组（build==host 保持 native 语义，
  AC_RUN_IFELSE 不被跳过；config.sub 2024-07-27 已接受 ohos 后缀）
- configure 的 config.status 临时目录用 umask 077 创建，HMDFS UID
  映射使 0700 目录进程不可写（E011，先例 a52dec）→ 0001 补丁改 umask 022
- src/jwk.c 错误清理路径读取声明点之后的 *_buflen，clang 15
  -Werror -Wsometimes-uninitialized 阻断 → 0002 补丁提升声明并初始化
- 依赖 jansson/openssl 由 conan 提供（PkgConfigDeps 生成 .pc +
  AutotoolsDeps 注入链接标志）
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class CjoseConan(ConanFile):
    name = "cjose"
    version = "0.6.2.7"
    description = "C-JOSE: an easy to use and easy to integrate C library implementing the JOSE standard"
    license = "MIT"
    homepage = "https://github.com/OpenIDC/cjose"
    url = "https://github.com/OpenIDC/cjose"
    topics = ("jose", "jws", "jwe", "jwk", "jwt")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("jansson/2.15.1.1")
        self.requires("openssl/3.5.8.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("cjose is supported only on Linux/OHOS")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # cjose.pc 上游声明 Requires: jansson, libcrypto；
        # PKG_CHECK_MODULES(CHECK) 需要 conan 侧生成的 .pc 环境
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()

        tc = AutotoolsToolchain(self)
        # configure 的 AC_CHECK_LIB 探测叠加显式依赖目录，保证链接探测命中
        tc.configure_args.append("--with-openssl={}".format(
            self.dependencies["openssl"].package_folder))
        tc.configure_args.append("--with-jansson={}".format(
            self.dependencies["jansson"].package_folder))
        if self.settings.os == "OHOS":
            # config.guess 不识别 HarmonyOS；build==host 保持 native 语义
            tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
            tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

        # configure 探测阶段（AC_CHECK_LIB）与产物运行期需要定位依赖动态库
        env = Environment()
        env.append_path("LD_LIBRARY_PATH",
                        os.path.join(self.dependencies["jansson"].package_folder, "lib"))
        env.append_path("LD_LIBRARY_PATH",
                        os.path.join(self.dependencies["openssl"].package_folder, "lib"))
        env.vars(self).save_script("conanruntime_env")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # 上游测试框架 check 未作为本包依赖（测试框架属上游测试阶段职责，
        # 不进包依赖链）；此环境下 have_check=no，make check 为 no-op。
        # 上游 85 个 check 用例在设备原生测试阶段以任务私有 libcheck 实跑
        # 85/85（见 notes.md 与 manifest.yaml upstream_tests）。
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # libtool *.la 记录打包机绝对路径，随包分发无意义
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE",
             src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["cjose"]
        # cjose.pc: Requires: jansson >= 2.3, libcrypto >= 1.0.1
        self.cpp_info.requires = ["jansson::jansson", "openssl::openssl"]
