#!/usr/bin/env python3
"""test_package — mesa 26.1.5 (HarmonyOS PC)

消费者视角验证：通过 Conan 解析出的 mesa 包，用真实 EGL + GLESv2 公共入口
完成一次离屏渲染往返。

与 24.3.4 系列的差异：上游 25.1.0 已移除 OSMesa，本版本不再有 libOSMesa，
离屏渲染改由 EGL pbuffer/surfaceless + llvmpipe 承担（用途等价）。

执行策略（重要）
----------------
OHOS 目标产物是 aarch64/musl ELF，本机（x86_64）无法直接执行，必须经
qemu-user 包装。因此测试**不能**依赖 `conan.tools.build.can_run()`：
该函数比较 build/host profile，用 `-pr:b=default` 时恒为 False，会让
`test()` 直接 return —— 表面"通过"，实则零验证（ZOMBIE TEST）。

本 conanfile 改为：
  1. 从 `tools.cmake.cmaketoolchain:extra_variables` 读取
     `CMAKE_CROSSCOMPILING_EMULATOR`；未配置时回落到已知的 qemu 包装器。
  2. 有包装器时**无条件执行**产物（交叉构建也要真跑），并把退出码作为
     测试结论；无包装器且无法本机执行时才显式跳过，且以 warning 记录。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


# 未显式配置 emulator 时的回落候选（按顺序取第一个存在的）。
# 与本仓库其他 OHOS 配方一致：qemu-user + OHOS musl 运行根。
_FALLBACK_EMULATORS = (
    "/root/ohpc/bin/ohos-qemu-aarch64",
    "/root/ohpc/bin/mesa-qemu-aarch64",
    "/root/ohpc/sdk/qemu/usr/bin/qemu-aarch64-static",
)


class MesaTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _emulator(self):
        """返回可用于执行目标产物的包装器命令（含参数），找不到返回 []。"""
        extra = self.conf.get(
            "tools.cmake.cmaketoolchain:extra_variables",
            default={}, check_type=dict) or {}
        raw = extra.get("CMAKE_CROSSCOMPILING_EMULATOR") or ""
        if raw:
            # CMake 的该变量是 `;` 分隔的列表，逐项 strip 后再拼成 argv
            parts = [p.strip() for p in str(raw).split(";") if p.strip()]
            if parts:
                return parts
        for cand in _FALLBACK_EMULATORS:
            if os.path.isfile(cand):
                return [cand]
        return []

    def generate(self):
        tc = CMakeToolchain(self)
        # 交叉构建时把 emulator 透传给 CMake，使 ctest / add_test 也能执行。
        emu = self._emulator()
        tc.cache_variables["CMAKE_CROSSCOMPILING_EMULATOR"] = ";".join(emu)
        tc.generate()
        self._emu = emu

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        emu = getattr(self, "_emu", None) or self._emulator()
        executable = os.path.join(self.cpp.build.bindirs[0], "test_mesa")
        if not os.path.isfile(executable):
            raise ConanException(
                "test_package build produced no test_mesa binary at %s" % executable)

        if emu:
            # 交叉目标经 qemu + OHOS musl 运行根真实执行。
            # conanrun 环境已由 package_info() 注入完整运行库查找路径。
            self.run(" ".join(emu + ['"%s"' % executable]), env="conanrun")
            return

        if self.settings.os == self.settings_build.os and \
                self.settings.arch == self.settings_build.arch:
            # 本机构建：直接执行
            self.run('"%s"' % executable, env="conanrun")
            return

        # 既无 emulator、又不可本机执行：显式告警，不用 info 静默放行。
        self.output.warning(
            "mesa test_package: 交叉目标 %s 无 qemu 包装器可用，消费者用例"
            "未执行（零验证）。请配置 "
            "tools.cmake.cmaketoolchain:extra_variables 的 "
            "CMAKE_CROSSCOMPILING_EMULATOR 后重跑。"
            % (self.settings.os,))
