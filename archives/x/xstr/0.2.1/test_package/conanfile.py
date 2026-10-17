#!/usr/bin/env python3
"""Conan test_package — xstr 0.2.1 (OCaml 库)

R34: 用 ocamlc 编译消费者程序 test.ml 并真正调用 xstr 库 API
（Xstr_search / Xstr_split / Xstr_match）断言已知结果，随后运行之。

HMBS 机器证据标记：
  - HMBS_TEST_PACKAGE_RESULT — 数字由 test.ml 真实输出的
    "xstr: N/M assertions passed" 解析而得（discovered=M, passedCount=N）
  - HMBS_UPSTREAM_TEST_RESULT — 上游无测试套件，status=no_tests（审计见
    MANIFEST.yml）；每轮都在 test() 复发以覆盖包缓存命中场景
"""
import json
import os
import re

from conan import ConanFile
from conan.tools.build import can_run


class XstrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _env(self, *keys):
        """解析 ocaml/xstr 依赖包的路径（统一 / 分隔，避免 Windows 反斜杠）。"""
        ocaml_pkg = self.dependencies["ocaml"]
        xstr_pkg = self.dependencies["xstr"]
        values = {
            "ocaml_bin": os.path.join(ocaml_pkg.package_folder, "bin").replace("\\", "/"),
            "ocaml_lib": os.path.join(ocaml_pkg.package_folder, "lib", "ocaml").replace("\\", "/"),
            "stublibs": os.path.join(ocaml_pkg.package_folder, "lib", "ocaml", "stublibs").replace("\\", "/"),
            "xstr_dir": os.path.join(xstr_pkg.package_folder, "lib", "xstr").replace("\\", "/"),
            "test_src": os.path.join(self.source_folder, "test.ml").replace("\\", "/"),
            "out": os.path.join(self.build_folder, "test_probe").replace("\\", "/"),
            "res": os.path.join(self.build_folder, "test_result.txt").replace("\\", "/"),
            "runner": os.path.join(self.source_folder, "run_test.sh").replace("\\", "/"),
        }
        return [values[k] for k in keys]

    def build(self):
        # 由 run_test.sh 统一驱动：设好 PATH/OCAMLLIB/CAML_LD_LIBRARY_PATH，
        # 用 ocamlc 链接 xstr.cma 编译 test.ml（ocaml 依赖包提供工具链）。
        ocaml_bin, ocaml_lib, stublibs, xstr_dir, test_src, out, res, runner = self._env(
            "ocaml_bin", "ocaml_lib", "stublibs", "xstr_dir", "test_src", "out", "res", "runner")
        self.run(
            'sh "{runner}" "{ocaml_bin}" "{ocaml_lib}" "{stublibs}" '
            '"{xstr_dir}" "{test_src}" "{out}" "{res}"'.format(
                runner=runner, ocaml_bin=ocaml_bin, ocaml_lib=ocaml_lib,
                stublibs=stublibs, xstr_dir=xstr_dir, test_src=test_src,
                out=out, res=res),
            env="conanrun",
        )

    def test(self):
        if can_run(self):
            # re-run the driver（覆盖包缓存命中时 build() 未必重跑的场景）
            ocaml_bin, ocaml_lib, stublibs, xstr_dir, test_src, out, res, runner = self._env(
                "ocaml_bin", "ocaml_lib", "stublibs", "xstr_dir", "test_src", "out", "res", "runner")
            # ignore_errors=True：若 test.ml 断言真实失败（exit 1）也不中断，
            # 仍据输出上报真实 passed:false，绝不伪造通过；输出已重定向到 res。
            self.run(
                'sh "{runner}" "{ocaml_bin}" "{ocaml_lib}" "{stublibs}" '
                '"{xstr_dir}" "{test_src}" "{out}" "{res}"'.format(
                    runner=runner, ocaml_bin=ocaml_bin, ocaml_lib=ocaml_lib,
                    stublibs=stublibs, xstr_dir=xstr_dir, test_src=test_src,
                    out=out, res=res),
                env="conanrun", ignore_errors=True)
            text = ""
            if os.path.exists(res):
                with open(res, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
            # 回显 test_probe 真实输出到日志，便于诊断断言结果
            for line in text.splitlines():
                self.output.info("test_probe: " + line)
            # 解析 test.ml 输出的真实断言计数
            m = re.search(r"xstr:\s*(\d+)/(\d+)\s+assertions passed", text)
            discovered = int(m.group(2)) if m else 9
            passed_count = int(m.group(1)) if m else 0
            tp_result = {
                "executed": True,
                "passed": passed_count == discovered and discovered > 0,
                "command": "./test_probe",
                "discovered": discovered,
                "passedCount": passed_count,
            }
            tp_text = json.dumps(tp_result)
            print("HMBS_TEST_PACKAGE_RESULT=" + tp_text, flush=True)
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + tp_text)
        # 上游无测试套件：no_tests（审计见 MANIFEST.yml）
        ut_result = {
            "status": "no_tests",
            "framework": "makefile",
            "command": "none (no upstream test suite)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": ("xstr 0.2.1 上游 tarball 已审计（xstr-0.2.1.tar.gz，"
                       "download.camlcity.org）：无 tests/test 目录、无 gtest/"
                       "def test_ 注册、Makefile 仅 all/opt/install/uninstall/"
                       "clean 目标（无 check/test）、speed/ 仅为基准示例、"
                       "无任何测试断言框架"),
        }
        ut_text = json.dumps(ut_result)
        print("HMBS_UPSTREAM_TEST_RESULT=" + ut_text, flush=True)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + ut_text)
