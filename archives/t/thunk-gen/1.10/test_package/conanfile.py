#!/usr/bin/env python3
"""Conan test_package — thunk-gen 1.10（消费者视角验证）.

thunk-gen 交付的是一组**构建期工具**：可执行文件 bin/thunk_gen/thunk_gen
与三个消费者脚本 parse_decls.sh / mkasmdefs.sh / tg_m4（同目录），以及
thunks.m4 / thunks32.m4 / thunk_gen.mk（res/thunk_gen/）。下游 dj64dev /
comcom64 / fdpp 的用法是"先筛声明、再编号、再喂给 thunk_gen"。

本 test_package 因此不复刻库链接，而是**只用包装好的产物**跑一遍真实消费者
管线：

  1. bash <pkg>/bin/thunk_gen/parse_decls.sh 1 consumer_decls.h | nl -v 0
  2. <pkg>/bin/thunk_gen/thunk_gen -a 4 -p 4            -> 生成 thunk_calls.h
  3. <pkg>/bin/thunk_gen/thunk_gen -a 4 -p 4 1 / 2      -> m4 模板 / C++ 宏形态
  4. 用生成的 thunk_calls.h 编译并运行 test_thunk_gen.c -> 逐条核对派发表语义

第 4 步是真实的编译 + 链接 + 运行；被 L1e 破坏性反向验证移走 bin/ 后必然
失败（R34：测试必须实质依赖被测包，不能是空壳）。

同时把 build() 期间记录的上游测试证据复发出去：Conan 命中包缓存时 build()
不再执行，HMBS_UPSTREAM_TEST_RESULT 只能从包内的 hmbs_upstream_result.json
还原（项目通行做法，见 aws-lc-tools/5.2.0）。
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException


class ThunkGenTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _dependency(self):
        for dep in self.dependencies.values():
            if dep.ref.name == "thunk-gen":
                return dep
        return None

    def _compiler(self):
        """R33：编译器取自 Conan conf，绝不裸用 shell 环境变量。"""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        return compilers.get("c") or "clang"

    def test(self):
        # ── 1) 复发上游测试证据（包缓存命中时 build() 不执行）──
        dep = self._dependency()
        if dep is not None and dep.package_folder:
            marker_file = os.path.join(str(dep.package_folder),
                                       "hmbs_upstream_result.json")
            if os.path.isfile(marker_file):
                try:
                    with open(marker_file, encoding="utf-8") as fh:
                        data = json.load(fh)
                    self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
                        {k: data.get(k) for k in
                         ("status", "framework", "command", "discovered",
                          "executed", "passed", "failed", "skipped")},
                        ensure_ascii=False))
                except (OSError, ValueError):
                    pass

        # ── 2) 消费者管线实跑 ──
        if dep is None or not dep.package_folder:
            raise ConanException("thunk-gen 依赖未解析，无法执行消费者验证")
        pkg = str(dep.package_folder)
        # OHOS 的 /system/bin/sh 不能直接执行 ELF，统一经 bash 驱动
        # （hmbs/CONFIG_SHELL 在真机上提供 bash）。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.isfile(bash):
            bash = "bash"
        cmd = f'"{bash}" test.sh "{pkg}" "{self._compiler()}"'
        self.run(cmd)
