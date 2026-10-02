#!/usr/bin/env python3
"""test_package — sbagen 1.4.5（消费者测试：CLI 产物契约 + C 侧 WAV 消费者 + Python CLI e2e）

上游 1.4.5 **不提供任何自动化测试**：发布包内没有 configure/Makefile（只有 mk* 构建
脚本），scripts/ 下的 t-*.sh 是交互式演示脚本（开篇 cat 使用说明 + `read xx` 等待
回车 → 实时播放音调 → ^C 结束），既无断言也无退出码语义，无法作为回归测试在 CI 中
运行；清点证据见 MANIFEST.yml。因此本包自带两层**真实消费者测试**，两层只使用打包产物：

1) test_cli_consumer.c —— C 侧消费者：直接 execv 打包好的 bin/sbagen 合成 2 秒立体声
   WAV，解析 RIFF/WAVE 头（2ch / 44100Hz / 16bit / data 长度），并校验左右声道非
   静音且互不相同（双耳拍频左右载波不同），最后检查 -h 的版本号。

2) sbagen_consumer_e2e.py —— 命令行 e2e：产物契约（含 ELF 架构为 aarch64）、-h
   版本、合成确定性（两次运行 sha256 一致）、raw/WAV 尺寸口径、混音生效、stdout
   管道输出、无音频设备时的明确提示（T_POSIX/NO_AUDIO 路径）、未编译解码器的优雅
   报错、上游示例序列合成。

环境约束：
  * E002：OHOS 目标机 /tmp 只读，编译与运行都需要显式可写 TMPDIR；
  * 编译/链接子进程**不注入** conan 依赖库目录到 LD_LIBRARY_PATH —— 本包零依赖，
    同时避免顶掉 SDK lld 自带运行库（thrulay 实测会导致 lld 启动即挂）；
  * OHOS 无 /bin/sh，故 C 侧消费者不用 system()/popen()，改用 fork+execv 捕获输出。
"""

import glob
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


class SbagenTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # ───────────────────────── 环境探测 ─────────────────────────

    def _c_compiler(self):
        """定位消费者用例的 C 编译器（profile conf → CC 环境变量 → PATH 探测）。

        不写死 SDK 绝对路径：R33 要求编译器来源可配置，硬编码机器路径跨机即失效。
        """
        exes = {}
        try:
            exes = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:  # conf 跨上下文不可读时退化为路径探测
            pass
        tried = []
        for cand in (exes.get("c"), os.environ.get("CC"), "clang", "cc", "gcc"):
            if not cand:
                continue
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
            found = shutil.which(cand)
            if found:
                return found
            tried.append(cand)
        raise ConanException(f"e2e: no usable C compiler (tried: {', '.join(tried)})")

    def _writable_tmpdir(self):
        """返回可写的临时目录（鸿蒙目标机 /tmp 只读，E002）。"""
        cand = os.environ.get("TMPDIR")
        if cand and os.path.isdir(cand) and os.access(cand, os.W_OK):
            return cand
        fallback = os.path.join(self.build_folder, "build", "tmp")
        os.makedirs(fallback, exist_ok=True)
        return fallback

    def _work_dir(self):
        """辅助产物目录：照仓库惯例统一放 build/。"""
        work = os.path.join(self.build_folder, "build")
        os.makedirs(work, exist_ok=True)
        return work

    # ───────────────────────── 编译消费者 ─────────────────────────

    def build(self):
        cc = self._c_compiler()
        tmpdir = self._writable_tmpdir()
        work = self._work_dir()
        out = os.path.join(work, "test_cli_consumer")

        cmd = [cc, "-std=gnu99", "-Wall",
               os.path.join(self.source_folder, "test_cli_consumer.c"),
               "-o", out]
        self.output.info("compiling C consumer: " + " ".join(cmd))

        # 编译/链接环境只注入 TMPDIR（见模块 docstring：绝不注入依赖库目录）
        build_env = Environment()
        build_env.define("TMPDIR", tmpdir)
        with build_env.vars(self).apply():
            subprocess.run(cmd, check=True)

    # ───────────────────────── 运行消费者 ─────────────────────────

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        pkg = dep.package_folder
        tmpdir = self._writable_tmpdir()
        work = self._work_dir()

        # ---- [0/3] 产物契约 ----
        exe = os.path.join(pkg, "bin", "sbagen")
        doc = os.path.join(pkg, "share", "doc", "sbagen", "SBAGEN.txt")
        examples = sorted(glob.glob(os.path.join(pkg, "share", "sbagen",
                                                "examples", "**", "*.sbg"),
                                    recursive=True))
        script = os.path.join(pkg, "share", "sbagen", "scripts", "p-drop")
        missing = [p for p in (exe, doc, script) if not os.path.isfile(p)]
        if missing:
            raise ConanException(f"打包产物缺失: {missing}")
        if not os.access(exe, os.X_OK):
            raise ConanException(f"可执行文件无执行权限: {exe}")
        if not examples:
            raise ConanException("包装产物缺失上游示例序列（share/sbagen/examples/*.sbg）")
        self.output.info(f"产物契约通过（含 {len(examples)} 个示例序列）")

        run_env = Environment()
        run_env.define("TMPDIR", tmpdir)

        # ---- [1/3] C 侧消费者：exec 打包二进制 → 解析 WAV 头 + 双声道校验 ----
        c_consumer = os.path.join(work, "test_cli_consumer")
        with run_env.vars(self).apply():
            self.run(f'"{c_consumer}" "{exe}" "{work}"')

        # ---- [2/3] CLI e2e：确定性/尺寸口径/混音/平台路径/解码器缺口 ----
        e2e = os.path.join(self.source_folder, "sbagen_consumer_e2e.py")
        with run_env.vars(self).apply():
            self.run(f'"{sys.executable}" "{e2e}" "{pkg}" "{work}"')

        # ---- [3/3] ----
        self.output.info("sbagen 消费者 e2e 全部通过（C 侧 WAV 消费者 + CLI e2e）")
