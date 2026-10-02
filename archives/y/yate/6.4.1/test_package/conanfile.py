#!/usr/bin/env python3
"""Conan test_package — yate L1 消费者测试（5 断言, R34 实质依赖）

断言 1: test.cpp 对 libyate 编译+链接+String API 行为调用（ctest 执行）
断言 2: yate -V 输出版本 6.4.1
断言 3: yate-config --cflags 输出非空
断言 4: yate.pc 元数据（Libs 含 -lyate; 有 pkg-config 时实测）
断言 5: yate -Dx 引擎初始化冒烟（含 SIP 模块加载成功）
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class YateTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        # yate 主包 package_type=application → conan 对 APP 类型消费者的默认 traits
        # 为 headers=False/libs=False（requires.py: APP → set_if_none 默认值）,
        # 本测试需真实编译头文件+链接 libyate（R34 实质依赖）, 必须显式开启
        self.requires(self.tested_reference_str, headers=True, libs=True)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 断言 1: C++ 消费者 编译+链接+API 行为（libyate 实质依赖）
        cmake = CMake(self)
        cmake.test()

        pkg = self.dependencies["yate"].package_folder
        yate = os.path.join(pkg, "bin", "yate")
        yate_config = os.path.join(pkg, "bin", "yate-config")

        def _run_capture(cmd, name):
            # 本版本 ConanFile.run 无输出捕获参数（返回 retcode）→
            # 命令内重定向到 build_folder 文件再读回（conanrun env 由 wrapper 应用）
            out_file = os.path.join(self.build_folder, f"{name}.out")
            self.run(f'{cmd} > "{out_file}" 2>&1', env="conanrun")
            with open(out_file) as f:
                return f.read()

        # 断言 2: 版本
        out = _run_capture(f'"{yate}" -V', "yate_V")
        assert "6.4.1" in out, f"yate -V 未输出 6.4.1: {out!r}"

        # 断言 3: yate-config 元数据
        out = _run_capture(f'"{yate_config}" --cflags', "yate_config_cflags")
        assert out.strip(), "yate-config --cflags 输出为空"

        # 断言 4: yate.pc 元数据
        pc = os.path.join(pkg, "lib", "pkgconfig", "yate.pc")
        assert os.path.isfile(pc), "yate.pc 缺失"
        with open(pc) as f:
            pc_content = f.read()
        assert "-lyate" in pc_content, "yate.pc Libs 缺 -lyate"
        if shutil.which("pkg-config"):
            out = _run_capture(
                f'PKG_CONFIG_PATH={os.path.join(pkg, "lib", "pkgconfig")} '
                f"pkg-config --libs yate",
                "pkgconfig_libs")
            assert "-lyate" in out, f"pkg-config --libs yate: {out!r}"

        # 断言 5: 引擎初始化冒烟（-Dx = init 后立即退出）+ SIP 模块加载
        # OHOS 无 pthread_cancel → 引擎软取消关闭路径存在非确定性挂起风险
        # （Thread.cpp 补丁禁用硬取消的已知限制, 见 notes.md）→ 用 30s 超时守卫,
        # 断言功能状态（初始化完成+SIP 模块加载, 均发生在 ~1s 内）而非退出码;
        # 初始化真失败时输出无相应标记 → 断言仍会失败
        out_file = os.path.join(self.build_folder, "yate_smoke.out")
        # 注: 系统 /bin/sh 拒绝 "VAR=x { ...; }" 复合命令前缀语法（syntax error）,
        # 且 conan wrapper = ". conanrun.sh && <cmd>" 经 /bin/sh -c 执行 →
        # 用子 shell 包裹, 仅依赖 sleep/kill/wait（toybox applet + 内置, 系统可靠存在）
        guarded = (
            f'( "{yate}" -Dx -c {os.path.join(pkg, "etc", "yate")} '
            f'-m {os.path.join(pkg, "lib", "yate")} '
            f'-e {os.path.join(pkg, "share", "yate")} '
            f'> "{out_file}" 2>&1 & p=$!; '
            f'( sleep 30; kill -9 $p 2>/dev/null ) & k=$!; '
            f'wait $p 2>/dev/null; kill $k 2>/dev/null; true; )')
        self.run(guarded, env="conanrun")
        with open(out_file) as f:
            out = f.read()
        assert "Yate engine is initialized" in out, \
            f"引擎初始化失败: {out[-500:]!r}"
        assert "SIP Channel" in out, "SIP 模块未加载"
        self.output.info("yate test_package: 5/5 assertions passed")
