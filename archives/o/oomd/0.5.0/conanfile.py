#!/usr/bin/env python3
"""Conan recipe — oomd 0.5.0（用户态 OOM killer，PSI + cgroupv2 强绑定）。

上游自述（README L18-L19）："oomd leverages PSI and cgroupv2 to monitor a
system holistically"；README L43："oomd requires PSI to function"。
构建系统 = meson（上游 .github/workflows/ci.yml：
    meson build/ && ninja -C build/ && ninja -C build/ test）。

依赖（W0 实测，制品仓 ohpcd 全部有预编译二进制，见 notes.md）：
  - jsoncpp/1.9.8        运行期（上游 meson.build dependency('jsoncpp')，
                         pkg-config 名 jsoncpp，实测产物 libjsoncpp.so）
  - meson/1.11.0         构建期 tool_requires（本机 PATH 无 meson）
  - gtest/1.17.0.2       构建期 test_requires（pkg-config 名 gtest /
                         gtest_main / gmock / gmock_main，供上游
                         dependency('gtest', main: true) 与 dependency('gmock')）
  - libsystemd           上游为 optional（dependency(..., required: false)），
                         制品仓无此包 ⇒ 上游 meson 自动跳过 systemd 插件
                         SystemdRestart 与其测试套件 systemd_plugin

平台适配要点（详见 notes.md 与 patches/）：
  1) 上游 meson.build 给可执行文件硬写 link_args: ['-lstdc++fs']（GCC 时代
     独立 filesystem 库）；OHOS clang 15 + libc++ 无此库，实测
     `ld.lld: error: unable to find library -lstdc++fs` ⇒ 补丁 0001 移除
     （C++17 std::filesystem 由 libc++ 原生提供，实测可编译可运行）。
  2) 上游 12 套件静态 207 宏、运行期发现 N=208（1 个 TEST_P 展开 2 例，
     见 notes.md §13.1）中 cgctx/MonitorRootHost 需要真实 cgroup2 挂载点，
     OHOS 上该用例按其自身 GTEST_SKIP 分支处理（详见 notes.md 测试口径）。
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain


class OomdConan(ConanFile):
    name = "oomd"
    version = "0.5.0"
    description = "oomd - userspace OOM killer leveraging PSI and cgroupv2"
    license = "GPL-2.0-only"
    homepage = "https://github.com/facebookincubator/oomd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("oom", "oom-killer", "psi", "cgroupv2", "memory-management")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("jsoncpp/1.9.8")

    def build_requirements(self):
        # 本机/CI worker PATH 无 meson（仓库 76 处同款先例：tool_requires meson/1.11.0）
        self.tool_requires("meson/1.11.0")
        # 上游 meson.build 只有在 gtest+gmock 均可解析时才编译测试套件
        self.test_requires("gtest/1.17.0.2")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # CI worker PATH 不含 llvm-ar/llvm-ranlib，meson project() 阶段探测
        # 链接器会失败；从 profile 的 compiler_executables 推导同目录工具
        # （archives/c/c-list/3.1.0 同款先例）
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("cpp") or compilers.get("c")
        if cc:
            tool_dir = os.path.dirname(cc)
            tc.binaries["ar"] = os.path.join(tool_dir, "llvm-ar")
            tc.binaries["ranlib"] = os.path.join(tool_dir, "llvm-ranlib")
        tc.generate()

        # 上游以 pkg-config 消费 jsoncpp / gtest / gmock，三者制品仓包内
        # 均带 .pc（实测 jsoncpp.pc、gtest.pc、gtest_main.pc、gmock.pc）
        pkgconfig = PkgConfigDeps(self)
        pkgconfig.generate()

    def build(self):
        apply_conandata_patches(self)

        # Meson 工具类不加载自定义 env，按 c-json 1.0.0 先例手动执行；
        # PKG_CONFIG_PATH 指向 PkgConfigDeps 生成目录（generators_folder）。
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "/data/service/hnp/bin/clang")
        cxx = compilers.get("cpp", "/data/service/hnp/bin/clang++")
        tool_dir = os.path.dirname(cxx)
        env_prefix = (
            f"PATH=/data/service/hnp/bin:$PATH "
            f"CC={cc} "
            f"CXX={cxx} "
            f"AR={os.path.join(tool_dir, 'llvm-ar')} "
            f"PKG_CONFIG_PATH={self.generators_folder}:$PKG_CONFIG_PATH "
        )

        self.run(
            env_prefix + "meson setup %s %s" % (self.build_folder, self.source_folder),
            cwd=self.build_folder,
            env="conanbuild",
        )
        # `--ninja-args '-k 0'`：编译阶段遇到可移植性错误时继续编译其余目标，
        # 一轮内暴露全部真实错误（ninja 仍以非零退出，成败语义不变）。
        self.run(
            "PATH=/data/service/hnp/bin:$PATH meson compile -C %s -j 2 "
            "--ninja-args '-k 0'" % self.build_folder,
            env="conanbuild",
        )
        # 上游官方测试入口（.github/workflows/ci.yml: ninja -C build/ test）：
        # 11 个核心 gtest 套件、静态 205 宏 / 运行期 206 例（第 12 套件
        # systemd_plugin 因无 libsystemd 不参与构建），随 conan create 真实执行。
        # OHOS 的 /tmp 是只读 erofs ⇒ 给测试进程显式 TMPDIR（上游 Fixture 的
        # getTempDir 与补丁后的 StatsTest/LogTest 都按 POSIX 约定读它），
        # 否则 CI 上 mkdtemp/mkstemp 落在 /tmp 必失败。
        test_tmp = os.path.join(self.build_folder, "test-tmp")
        os.makedirs(test_tmp, exist_ok=True)
        self.run(
            "TMPDIR=%s TEMP=%s PATH=/data/service/hnp/bin:$PATH meson test "
            "-C %s --print-errorlogs --num-processes 2 --timeout-multiplier=10"
            % (test_tmp, test_tmp, self.build_folder),
            env="conanbuild",
        )

    def package(self):
        # HMDFS 上不做 meson install（符号链接链易碎），按产物实体拷贝
        # （c-json 1.0.0 先例）。
        # 可执行目标定义在顶层 meson.build ⇒ 产物落在构建根 `<build>/oomd`
        # （b2 轮实测：`<build>/oomd` 存在（19MB）、`<build>/src/oomd` 不存在，
        #   包内 bin/ 缺失导致 test_package 报 "oomd binary not found in package bindirs"）。
        copy(
            self,
            "oomd",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        # configure_file 产物（上游 oomd.service.in / desktop.json）
        copy(
            self,
            "oomd.json",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "etc", "oomd"),
        )
        copy(
            self,
            "oomd.service",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib", "systemd", "system"),
        )
        copy(
            self,
            "oomd.1",
            src=os.path.join(self.source_folder, "man"),
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
        )

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "oomd")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
