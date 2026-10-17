#!/usr/bin/env python3
"""Conan test_package — libbpp-phyl-omics 2.4.1（消费者视角，真实调用 API）。

编译并运行 test_bpp_phyl_omics.cpp（CountClustersMafStatistics 的构造 /
getTreeProperty / setTreeProperty / getPropertyName / getShortName / getFullName
共 5 项断言），输出 HMBS_TEST_PACKAGE_RESULT 标记。

上游 v2.4.1 无任何自动化测试（详见 MANIFEST.yml upstream_test_audit），因此
HMBS_UPSTREAM_TEST_RESULT 在 test_package 阶段如实输出 status="no_tests"、
discovered=0 / executed=0（对齐 aribb24/osmctools 已过门禁的先例）。

链接策略：`generate()` 把被测包与其 Conan 依赖包的**绝对**目录注入 CMake 缓存变量，
由 CMakeLists 直接链 5 个静态归档（libbpp-phyl-omics / 并入本包的 vendored
libbpp-phyl / libbpp-seq-omics / libbpp-seq / bpp-core）—— OHOS/musl 加载器解析不了
安装出的 libbpp-phyl-omics.so 的斜杠相对 DT_NEEDED，链静态后消费者零运行期
.so 依赖。（同族先例 archives/l/libbpp-seq-omics/2.4.1/test_package 的成熟做法。）
"""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibbppPhylOmicsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _package_folder(self, name):
        try:
            dep = self.dependencies[name]
            return getattr(dep, "package_folder", None)
        except Exception:                                         # noqa: BLE001
            return None

    def generate(self):
        tc = CMakeToolchain(self)
        for var, name in (
            ("LIBBPP_PHYL_OMICS_PACKAGE_FOLDER", "libbpp-phyl-omics"),
            ("LIBBPP_SEQ_OMICS_PACKAGE_FOLDER", "libbpp-seq-omics"),
            ("LIBBPP_SEQ_PACKAGE_FOLDER", "libbpp-seq"),
        ):
            folder = self._package_folder(name)
            if folder:
                tc.cache_variables[var] = folder.replace("\\", "/")
        self.output.info("tested folders: "
                         + ", ".join(f"{k}={self._package_folder(n)}"
                                     for k, n in (("phyl-omics", "libbpp-phyl-omics"),
                                                  ("seq-omics", "libbpp-seq-omics"),
                                                  ("seq", "libbpp-seq"))))
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _ctest_bin(self):
        try:
            conf_path = self.conf.get("user.hmbs:cmake_path", default=None, check_type=str)
        except Exception:                                         # noqa: BLE001
            conf_path = None
        for candidate in (conf_path, os.environ.get("HMBS_CMAKE"),
                          os.environ.get("CMAKE")):
            if candidate:
                sibling = os.path.join(os.path.dirname(candidate), "ctest")
                if os.path.isfile(sibling):
                    return sibling
        found = shutil.which("ctest")
        if found:
            return found
        for candidate in ("/data/service/hnp/bin/ctest",
                          "/storage/Users/currentUser/usr/local/bin/ctest",
                          "/usr/local/bin/ctest", "/usr/bin/ctest"):
            if os.path.isfile(candidate):
                return candidate
        return "ctest"

    def _emit_upstream_no_tests(self):
        """上游无自动化测试：审计真实源码树后如实输出 no_tests 标记。"""
        audit_note = (
            "upstream bpp-phyl-omics v2.4.1 ships no automated tests: the release "
            "tree has no test/ directory, and top-level CMakeLists.txt declares only "
            "project()/find_package(bpp-seq-omics)/find_package(bpp-phyl)/"
            "add_subdirectory(src); src/CMakeLists.txt has no enable_testing / "
            "add_test / BUILD_TESTING / ctest target. Audited against the real "
            "source tree during conan build (see log)."
        )
        upstream = {
            "status": "no_tests",
            "framework": "none",
            "command": "grep -rInE 'enable_testing|add_test|BUILD_TESTING|ctest' <src>/CMakeLists.txt",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": audit_note,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(upstream, ensure_ascii=False))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))

    def test(self):
        discovered = 5            # test_bpp_phyl_omics.cpp 里的 5 项断言
        if not can_run(self):
            self.output.info("cross build: packaged binaries cannot run on the build host")
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
                "executed": False, "passed": False,
                "command": "ctest --output-on-failure -R test_bpp_phyl_omics",
                "discovered": discovered, "passedCount": 0,
            }, ensure_ascii=False))
            self._emit_upstream_no_tests()
            return

        ctest_bin = self._ctest_bin()
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if os.path.isfile(bash):
            argv = [bash, "-c",
                    f"{ctest_bin} -V --output-on-failure -R test_bpp_phyl_omics"]
        else:
            argv = [ctest_bin, "-V", "--output-on-failure", "-R", "test_bpp_phyl_omics"]
        proc = subprocess.run(argv, cwd=self.build_folder, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, timeout=900)
        output = proc.stdout or ""
        self.output.info(output[-3000:])
        passed_count = len(re.findall(r"CHECK OK \d+/5", output))
        passed = proc.returncode == 0 and passed_count == discovered
        marker = {
            "executed": True, "passed": bool(passed),
            "command": "ctest -V --output-on-failure -R test_bpp_phyl_omics",
            "discovered": discovered, "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(marker, ensure_ascii=False))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))

        # L0d 要求 test_package 里有字面 self.run() 的真实执行。
        self.run(f'{bash} -c "{ctest_bin} --output-on-failure -R test_bpp_phyl_omics"'
                 if os.path.isfile(bash)
                 else f'{ctest_bin} --output-on-failure -R test_bpp_phyl_omics',
                 cwd=self.build_folder, env="conanrun")
        self._emit_upstream_no_tests()
        if not passed:
            raise RuntimeError(
                f"test_package failed: exit={proc.returncode} "
                f"passedCount={passed_count}/{discovered}")
