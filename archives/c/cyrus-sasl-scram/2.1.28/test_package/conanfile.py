#!/usr/bin/env python3
"""Conan test_package — cyrus-sasl-scram 2.1.28 消费者测试。

用 CMakeDeps + CMakeToolchain 把 test_scram.c 链接到打包的静态 libsasl2.a，
在原生 OHOS 目标上运行：

  * 运行 1 (`./test_scram`)                       — 8 项检查，按 "CHECK-OK:" 行
    计数（仅凭 exit 0 不足以作为证据）。
  * 运行 2 (`SASL_PATH=<不存在的目录> ./test_scram --ohos-static-only`)
    — 鸿蒙特有断言：没有运行期插件目录时 SCRAM 家族仍须被枚举出来，
    因为机制静态链入 libsasl2.a（--enable-scram + 静态构建，无 dlopen）。

上游测试证据：cyrus-sasl 2.1.28 不注册 automake `make check`，但自带
自动化测试台 utils/testsuite.c（EXTRA_PROGRAMS）；本配方在 build() 中
真实构建并运行它（默认 db_none 闭包下停在需要口令库的 `test_checkpass`
阶段，marker 如实记录）；完整 sasldb/LMDB 闭包下的逐阶段读数见
2.1.28/reports/upstream-tests.md。
"""

import json
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout

# test_scram.c 默认模式恰好 8 项检查，每项成功打印一行 "CHECK-OK: <name>"。
CONSUMER_CHECK_COUNT = 8
OHOS_STATIC_CHECK = "CHECK-OK: ohos-static-scram-no-saslpath"


class CyrussaslscramTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _ensure_writable_tmp(self):
        # HMBS 在真机上注入任务私有可写 TMPDIR（/tmp 只读 [readonly_tmp]）。
        # CMake/ctest/被测二进制全程避开 /tmp。
        tmp = None
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate and os.path.isdir(candidate):
                tmp = candidate
                break
        if not tmp:
            tmp = os.path.join(self.build_folder, "hmbs-tmp")
            os.makedirs(tmp, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        return tmp

    def build(self):
        self._ensure_writable_tmp()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _test_binary(self):
        return os.path.join(self.cpp.build.bindirs[0], "test_scram")

    def _log_package_libs_for_ohos(self):
        # 诊断静态/动态混淆：包内只应有 libsasl2.a（shared=False）。
        try:
            pkg = self.dependencies[self.tested_reference_str].package_folder
        except Exception:
            try:
                pkg = self.dependencies["cyrus-sasl-scram"].package_folder
            except Exception:
                return
        libdir = os.path.join(str(pkg), "lib")
        try:
            names = sorted(os.listdir(libdir))
        except OSError as exc:
            self.output.info("package libdir missing %s: %s" % (libdir, exc))
            return
        self.output.info("package libdir %s: %s" % (libdir, ", ".join(names)))

    def _run_consumer_binary(self, args, env_extra=None):
        bin_path = self._test_binary()
        if not os.path.isfile(bin_path):
            raise ConanException("test binary missing: %s" % bin_path)
        env = dict(os.environ)
        if env_extra:
            env.update(env_extra)
        proc = subprocess.run(
            [bin_path] + list(args),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
        output = proc.stdout or ""
        self.output.info(output[-4000:])
        return proc.returncode, output

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link test completed")
            return
        self._ensure_writable_tmp()
        self._log_package_libs_for_ohos()

        cmake = CMake(self)
        try:
            cmake.test()
        except Exception as exc:
            # 不丢证据：ctest 失败也把真实输出与 marker 打出来。
            self.output.warning("ctest failed: %s" % exc)
            self._run_consumer_binary([])
            raise

        rc, output = self._run_consumer_binary([])
        ok_count = output.count("CHECK-OK:")
        marker = {
            "executed": True,
            "passed": rc == 0 and ok_count == CONSUMER_CHECK_COUNT,
            "command": self._test_binary(),
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": ok_count,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if not marker["passed"]:
            raise ConanException(
                "consumer test failed: rc=%s ok=%s/%s"
                % (rc, ok_count, CONSUMER_CHECK_COUNT)
            )

        # 鸿蒙特有断言：完全没有运行期插件目录。
        missing_dir = os.path.join(self.build_folder, "hmbs-no-plugin-dir")
        ohos_rc, ohos_output = self._run_consumer_binary(
            ["--ohos-static-only"], env_extra={"SASL_PATH": missing_dir}
        )
        ohos_ok = ohos_rc == 0 and OHOS_STATIC_CHECK in ohos_output
        self.output.info(
            "HMBS_OHOS_STATIC_RESULT="
            + json.dumps(
                {
                    "executed": True,
                    "passed": ohos_ok,
                    "command": "%s --ohos-static-only" % self._test_binary(),
                    "sasl_path": missing_dir,
                    "check": OHOS_STATIC_CHECK,
                },
                ensure_ascii=False,
            )
        )
        if not ohos_ok:
            raise ConanException(
                "OHOS static-mechanism check failed: rc=%s" % ohos_rc
            )

        # L0d 质量门禁：二进制也要能在 conanrun 环境下执行。
        self.run(self._test_binary(), env="conanrun")
        self._emit_upstream_marker()
        self.output.info("cyrus-sasl-scram consumer test_package passed")

    def _emit_upstream_marker(self):
        # 上游测试台由 conanfile.py 的 build() 构建并运行；完整逐阶段读数
        # （sasldb/LMDB 闭包，10/19 阶段通过、1 阶段失败、8 阶段未到达）见
        # 2.1.28/reports/upstream-tests.md，本 marker 只记交付闭包的真实读数。
        upstream_marker = {
            "status": "run_in_package_build",
            "framework": "cyrus-utils-testsuite",
            "command": "make -C utils testsuite && SASL_PATH=<empty> ./utils/testsuite",
            "discovered": 19,
            "executed": 1,
            "passed": 0,
            "failed": 1,
            "skipped": 18,
            "reason": (
                "cyrus-sasl 2.1.28 不注册 automake TESTS/check_PROGRAMS（无 "
                "make check 目标），唯一自包含断言测试台是 utils/testsuite.c"
                "（main() 中 19 个标号阶段）。它被真实构建并运行："
                "交付闭包为 --with-dblib=none，testsuite 的第 1 阶段 "
                "test_checkpass 需要已初始化的 sasldb 口令库，故停在 "
                "'Checking plaintext passwords... Failed with: sasl_checkpass()'。"
                "在独立 sasldb/LMDB 临时测试树中的完整运行见 "
                "2.1.28/reports/upstream-tests.md：10 个阶段通过、"
                "第 11 阶段（client-first/server-last 的 SCRAM-SHA-256）"
                "报 sasl_server_start() error、其余阶段未到达（8/8 seed 稳定复现）。"
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_marker, ensure_ascii=False)
        )
