#!/usr/bin/env python3
"""Conan test_package — pcb 4.3.0 binary functional verification.

pcb 是纯命令行应用（batch HID），无 C API。按可执行 test_package 模式，
test() 通过子进程驱动上游数据用例与新增用例：
  run_pcb_tests.sh <pcb> <datadir>
  * 上游行为复现 3 场景/7 断言（pcb 官方 tests/ 回归套件同款输入/输出，
    tests/golden 文本比对，见 MANIFEST.yml）: bom(bom+xy) / bom_md /
    IPC-D-356 导出。
  * 新增测试 7 断言（上游未覆盖）: version/help、缺文件与空输入无崩溃
    回归（0006 bugfix 守护）、非法内容/未知 HID/未知选项错误路径。
计数口径（上游复现 7 断言 + 新增 7 断言 = 14）与 run_pcb_tests.sh、
CMakeLists.txt、MANIFEST.yml、版本 manifest.yaml 与 PR 描述五处同步。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException


class PcbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["pcb"]
        pcb_bin = os.path.join(dep.package_folder, "bin", "pcb")
        if not os.path.exists(pcb_bin):
            raise ConanException(f"pcb binary not found: {pcb_bin}")

        # pcb 动态链接 conan glib(链)共享库；运行时把依赖 libdirs 前置到
        # LD_LIBRARY_PATH（OHOS 系统自带旧/stub glib 缺 g_list_last 等符号，
        # 与 chafa 同款处理）
        libdirs = []
        for d in self.dependencies.host.values():
            if not d.package_folder:
                continue
            for ld in d.cpp_info.libdirs:
                p = ld if os.path.isabs(ld) else os.path.join(d.package_folder, ld)
                if os.path.isdir(p):
                    libdirs.append(p)
        if libdirs:
            current = [x for x in os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep) if x]
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(libdirs + current)
        # 全部产物/临时文件收口到 build_folder 内 scratch（不污染 recipe 目录）
        scratch = os.path.join(self.build_folder, ".pcb-test-scratch")
        shutil.rmtree(scratch, ignore_errors=True)
        os.makedirs(scratch, exist_ok=True)
        os.environ["TMPDIR"] = scratch

        driver = os.path.join(self.recipe_folder, "run_pcb_tests.sh")
        data_dir = os.path.join(self.recipe_folder, "data")
        self.run(f'sh "{driver}" "{pcb_bin}" "{data_dir}"')
        self.output.success("pcb test_package PASSED")
