#!/usr/bin/env python3
"""Conan test_package for libwapcaplet 0.4.3 — L1 smoke test.

CI runs this automatically via `conan create` (which invokes test_package).
test.c exercises the real lwc_string_* API of the package (R34).

Machine evidence (HMBS preflight hard gate):
- runs the consumer binary via subprocess, parses the
  "libwapcaplet API assertions: N passed" line and emits
  HMBS_TEST_PACKAGE_RESULT with real discovered/passedCount numbers
  (exit code 0 alone is not accepted as proof);
- re-emits the persisted HMBS_UPSTREAM_TEST_RESULT (package res/
  hmbs_upstream.json) so the evidence gate also sees upstream results
  on Conan cache hits where recipe build() is skipped.
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout

# test.c 中的断言总数（与 test.c 的 assertions 累加一致）
CONSUMER_ASSERT_COUNT = 16


class LibwapcapletTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # E120: OHOS SDK lld 链接 libxml2.so.16；把 SDK llvm 的 lib 目录
        # 注入 LD_LIBRARY_PATH，让 CMake configure/link 阶段能找到它
        # （CI worker 上该路径不在默认 loader 搜索路径）。
        sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        if os.path.isdir(sdk_lib):
            os.environ["LD_LIBRARY_PATH"] = sdk_lib + ":" + os.environ.get("LD_LIBRARY_PATH", "")

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # R34 / L0d (CI): test() 必须真正执行被测二进制（self.run），
        # 不能是空壳。先用 ctest 运行，再直接执行二进制双保险验证。
        cmake = CMake(self)
        cmake.test()

        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libwapcaplet")
        if not os.path.isfile(bin_path):
            raise ConanException("test binary missing: %s" % bin_path)
        run = subprocess.run(
            [bin_path],
            env=dict(os.environ),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
        output = run.stdout or ""
        self.output.info(output)
        passed = 0
        match = re.search(r"libwapcaplet API assertions:\s*(\d+)\s*passed", output)
        if match:
            passed = int(match.group(1))
        ok = run.returncode == 0 and passed == CONSUMER_ASSERT_COUNT
        marker = {
            "executed": True,
            "passed": ok,
            "command": bin_path,
            "discovered": CONSUMER_ASSERT_COUNT,
            "passedCount": passed,
        }
        msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        # 双通道输出（stdout + Conan output）：HMBS 预检抓取原始 stdout
        print(msg, flush=True)
        self.output.info(msg)
        if not ok:
            raise ConanException(
                "consumer test failed: rc=%s passed=%s/%s"
                % (run.returncode, passed, CONSUMER_ASSERT_COUNT)
            )
        # L0d 门禁要求 test() 内有字面 self.run 真实执行（沿用 0.4.3.2 既定写法；
        # OHOS /system/bin/sh (mksh) 无法直接 exec ELF 二进制，用 bash 包裹）
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c '{bin_path}'", env="conanrun")

        # 缓存命中复发：Conan 复用已安装包时 recipe build() 被跳过，
        # 其 HMBS_UPSTREAM_TEST_RESULT 不会打印。此处复发包内持久化的真实
        # 结果（build() 写入 res/hmbs_upstream.json），证据门禁每轮可见。
        # 不重新定义任何测试；数字即 build() 内真实的上游等价检查结果。
        try:
            upstream = None
            pkg_name = (self.tested_reference_str.split("/")[0]
                        if "/" in self.tested_reference_str else "libwapcaplet")
            try:
                dep = self.dependencies[pkg_name]
                pkg_folder = getattr(dep, "package_folder", None)
                if pkg_folder:
                    cand = os.path.join(pkg_folder, "res", "hmbs_upstream.json")
                    if os.path.isfile(cand):
                        with open(cand, "r", encoding="utf-8") as fh:
                            upstream = json.load(fh)
            except Exception:
                upstream = None
            if isinstance(upstream, dict) and upstream.get("discovered"):
                umsg = ("HMBS_UPSTREAM_TEST_RESULT="
                        + json.dumps(upstream, ensure_ascii=False))
                print(umsg, flush=True)
                self.output.info(umsg)
            else:
                self.output.warning(
                    "persisted hmbs_upstream.json missing; "
                    "upstream evidence only available on fresh build")
        except Exception as e:
            self.output.warning("upstream re-emit failed: %r" % (e,))
