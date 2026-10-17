#!/usr/bin/env python3
"""Conan recipe — carbon-c-relay 3.7.3（Graphite 集群感知指标中继/路由器）。

C + autotools，产物为应用二进制 relay（R38：软件级 commands.json）。
零 conan 依赖：gzip 走 OHOS sysroot 自带 zlib；openssl/lz4/snappy/onig/pcre
设备 sysroot 无头文件，configure 自动禁用（不 --with 不引入）。
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CarbonCRelayConan(ConanFile):
    name = "carbon-c-relay"
    version = "3.7.3"
    description = "carbon-c-relay — cluster-aware Graphite metric relay and router"
    license = "Apache-2.0"
    homepage = "https://github.com/grobian/carbon-c-relay"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # E007: 上游自带 config.guess 无法识别 HarmonyOS uname，显式指定三元组
        # （build=linux-gnu 与 host=ohos 不同 → 按交叉处理，不在构建机运行目标
        #   程序；两个都写 ohos 会触发 "cannot run C compiled programs"，
        #   同 ekg2 0.3.1 先例）
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-ohos",
        ])
        # 名义交叉下 AC_FUNC_MALLOC/AC_FUNC_REALLOC 的运行探针按失败处理，
        # 会把 malloc 定义成不存在的 rpl_malloc 导致编译失败；以 cache 变量
        # 如实声明 glibc/musl 均满足的 malloc(0)/realloc(NULL,0) 非 NULL 语义
        tc.configure_args.append("ac_cv_func_malloc_0_nonnull=yes")
        tc.configure_args.append("ac_cv_func_realloc_0_nonnull=yes")
        tc.generate()

    def _fs_env(self):
        """HMBS 平台诊断 [shell_getcwd]（同 adcli 0.9.2 先例）：HMDFS 拒绝对
        conan 构建树父目录的 getcwd()，bash/autoconf 的 pwd 失败
        （"configure: error: working directory cannot be determined"）。
        autoconf 优先读 $PWD 环境变量（bash 从环境初始化 $PWD 而不调
        getcwd()），显式设 PWD 并固定 TMPDIR/TMP/TEMP 为可写目录。"""
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP")
                  or os.path.join(self.build_folder, ".tmp"))
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("PWD", self.build_folder)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        return env

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        with self._fs_env().vars(self).apply():
            autotools.configure()
            autotools.make(args=["-j1"])

    def package(self):
        # 不走 make install（HMDFS 安装路径不可控），直接拷贝构建产物
        copy(self, "relay", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
