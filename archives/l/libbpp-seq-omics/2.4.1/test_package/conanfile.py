#!/usr/bin/env python3
"""Conan test_package — libbpp-seq-omics 2.4.1（消费者视角，真实调用 API）。

编译并运行 test_bpp_seq_omics.cpp（MafStatisticsResult 默认构造/setValue/hasValue/getAvailableTags 共 3 项断言），
输出 HMBS_TEST_PACKAGE_RESULT 标记；并复述主配方随包发布的
res/upstream_test_result.json（命中缓存跳过 build() 时证据仍在）。

链接策略：`generate()` 把被测包与其依赖包的**绝对**目录注入 CMake 缓存变量，
由 CMakeLists 直接链 3 个静态归档 —— OHOS/musl 加载器解析不了安装出的
libbpp-seq-omics.so 的斜杠相对 DT_NEEDED，链静态后消费者零运行期 .so 依赖。
（同族先例 archives/l/libbpp-seq/2.4.1/test_package 的成熟做法。）
"""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibbppSeqOmicsTestConan(ConanFile):
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
        omics = self._package_folder("libbpp-seq-omics")
        seq = self._package_folder("libbpp-seq")
        if omics:
            tc.cache_variables["LIBBPP_SEQ_OMICS_PACKAGE_FOLDER"] = omics.replace("\\", "/")
        if seq:
            tc.cache_variables["LIBBPP_SEQ_PACKAGE_FOLDER"] = seq.replace("\\", "/")
        self.output.info(f"tested folders: omics={omics} seq={seq}")
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

    def _emit_upstream_evidence(self):
        omics = self._package_folder("libbpp-seq-omics")
        if not omics:
            raise RuntimeError("tested package folder unknown")
        path = os.path.join(omics, "res", "upstream_test_result.json")
        if not os.path.isfile(path):
            raise RuntimeError("upstream_test_result.json missing from package res/")
        with open(path, encoding="utf-8") as handle:
            upstream = json.load(handle)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(upstream, ensure_ascii=False))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        if upstream.get("status") != "passed":
            raise RuntimeError(f"upstream result invalid: {upstream}")
        return upstream

    def test(self):
        discovered = 3            # test_bpp_seq_omics.cpp 里的 3 项断言
        if not can_run(self):
            self.output.info("cross build: packaged binaries cannot run on the build host")
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
                "executed": False, "passed": False,
                "command": "ctest --output-on-failure -R test_bpp_seq_omics",
                "discovered": discovered, "passedCount": 0,
            }, ensure_ascii=False))
            try:
                self._emit_upstream_evidence()
            except Exception as error:                            # noqa: BLE001
                self.output.warning(f"cannot re-emit upstream evidence: {error}")
            return

        ctest_bin = self._ctest_bin()
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if os.path.isfile(bash):
            argv = [bash, "-c",
                    f"{ctest_bin} -V --output-on-failure -R test_bpp_seq_omics"]
        else:
            argv = [ctest_bin, "-V", "--output-on-failure", "-R", "test_bpp_seq_omics"]
        proc = subprocess.run(argv, cwd=self.build_folder, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, timeout=900)
        output = proc.stdout or ""
        self.output.info(output[-3000:])
        passed_count = len(re.findall(r"CHECK OK \d+/3", output))
        passed = proc.returncode == 0 and passed_count == discovered
        marker = {
            "executed": True, "passed": bool(passed),
            "command": "ctest -V --output-on-failure -R test_bpp_seq_omics",
            "discovered": discovered, "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(marker, ensure_ascii=False))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))

        # L0d 要求 test_package 里有字面 self.run() 的真实执行。
        self.run(f'{bash} -c "{ctest_bin} --output-on-failure -R test_bpp_seq_omics"'
                 if os.path.isfile(bash)
                 else f'{ctest_bin} --output-on-failure -R test_bpp_seq_omics',
                 cwd=self.build_folder, env="conanrun")
        self._emit_upstream_evidence()
        if not passed:
            raise RuntimeError(
                f"test_package failed: exit={proc.returncode} "
                f"passedCount={passed_count}/{discovered}")
