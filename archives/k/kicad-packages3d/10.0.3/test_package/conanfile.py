#!/usr/bin/env python3
"""Conan test_package for kicad-packages3d — 消费者视角验证被测包。

本包是纯数据/资源包（无 C/C++ 产物、无 bin/），因此 R34 的“实质依赖”体现为
**真实读取并解析包内数据**：测试脚本从 ``self.dependencies["kicad-packages3d"].package_folder``
取出已安装的 3D 模型目录，校验安装布局、模型覆盖度（105 个 ``*.3dshapes`` 目录 /
7238 个 STEP 模型）、每个 STEP 文件的有效性与已知经典模型存在性。

负向验证：把包产物移走后本测试必然失败（模型目录与模型文件全部找不到），
即测试确实依赖被测包而非空壳（见 reports/test-report.md）。
"""
import json
import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["kicad-packages3d"].package_folder
        script = os.path.join(self.recipe_folder, "test_kicad_packages3d.py")
        # 用 shell 形式显式传包目录；-B 避免在只读/HMDFS 路径下写 __pycache__
        self.run('python3 -B "%s" "%s"' % (script, pkg_folder), env="conanrun")

        # HMBS 机器证据标记：上游 no_tests（见 test_package/MANIFEST.yml 的
        # upstream_test_audit 审计结论——上游仓库没有任何测试，upstream_test_total: 0）。
        # 在真实运行 test_package 之后再复发行，status=no_tests、各计数为 0。
        upstream_marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": ("upstream kicad-packages3d 10.0.3 无任何测试；审计见 "
                       "test_package/MANIFEST.yml 的 upstream_test_audit（project NONE、"
                       "无 enable_testing/add_test/CTest/BUILD_TESTING、0 个 C/C++ 源、"
                       "0 个 Python/Shell 脚本、无 CI 测试配置），upstream_test_total: 0"),
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker))
