#!/usr/bin/env python3
"""Conan recipe — raul 2.0.0（实时音频工具库，纯头文件 C++17）.

raul 是 David Robillard 的实时音频工具库，LV2 生态中 Ingen、Patchage 等程序的
公共基础依赖。2.0.0 无编译库目标：上游 Meson 仅安装头文件
（include/raul-2/raul/*.hpp）与 pkg-config（raul-2.pc），测试为 11 个自包含
可执行文件（10 个单元测试 + test_headers），全部经 meson test 注册。

上游测试套件在 build() 内经 meson test 随 conan create 在目标平台真实执行，
输出 HMBS_UPSTREAM_TEST_RESULT 机器可读标记（executed/passed/failed）。
交叉编译环境仅编译验证（can_run 守卫）。

已知平台差异：OHOS 安全策略拒绝 AF_UNIX bind（/tmp 只读 EROFS=30，可写目录
同样 EPERM=1；TCP 回环正常），上游 socket_test 的 UNIX 用例不可执行。补丁
0001 在 bind 因平台策略失败（EPERM/EROFS/EACCES）时按 meson 约定以退出码 77
跳过（SKIP），其他 errno 仍返回 1（FAIL），不掩盖真实缺陷。
"""
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class RaulConan(ConanFile):
    name = "raul"
    version = "2.0.0"
    description = "Raul - real-time audio utility library (header-only C++17)"
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.com/drobilla/raul"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("audio", "real-time", "header-only", "lv2")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # 上游构建系统为 Meson；meson/1.11.0 已发布到制品仓（c-list 同款先例）
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self)

    def package_id(self):
        # 纯头文件库：所有 settings 组合产出相同包内容
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = MesonToolchain(self)
        # CI worker 的 PATH 不含 llvm-ar/llvm-ranlib（c-list/account-utils 先例）：
        # 从 profile compiler_executables 推导同目录工具写入 machine file [binaries]
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp") if compilers else None
        if cxx:
            tool_dir = os.path.dirname(cxx)
            tc.binaries["ar"] = os.path.join(tool_dir, "llvm-ar")
            tc.binaries["ranlib"] = os.path.join(tool_dir, "llvm-ranlib")
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()
        if can_run(self):
            self._run_upstream_tests()
        else:
            self.output.info("cross-building: upstream meson test skipped (compile-only)")

    def _run_upstream_tests(self):
        """Run the upstream Meson suite and emit HMBS_UPSTREAM_TEST_RESULT."""
        log = os.path.join(self.build_folder, "meson-test.log")
        rc = self.run(
            'meson test -C "{}" --print-errorlogs > "{}" 2>&1'.format(self.build_folder, log),
            ignore_errors=True)
        content = ""
        if os.path.exists(log):
            with open(log, encoding="utf-8", errors="replace") as handle:
                content = handle.read()

        def count(label):
            match = re.search(r"^{}:\s+(\d+)\s*$".format(label), content, re.MULTILINE)
            return int(match.group(1)) if match else 0

        ok = count("Ok")
        failed = count("Fail") + count("Unexpected Pass") + count("Timeout")
        skipped = count("Skipped")
        expected_fail = count("Expected Fail")
        executed = ok + failed
        upstream = {
            "status": "passed" if (rc == 0 and executed > 0 and failed == 0) else "failed",
            "framework": "meson-test",
            "command": "meson test -C . --print-errorlogs",
            "discovered": executed + skipped + expected_fail,
            "executed": executed,
            "passed": ok,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        if upstream["status"] != "passed":
            self.output.error(content[-4000:])
            raise ConanException("upstream raul meson tests failed (rc={})".format(rc))

    def package(self):
        # 上游 install_headers + pkg.generate：头文件 → include/raul-2/raul/，
        # pkg-config → lib/pkgconfig/raul-2.pc（纯文件拷贝，无符号链接）
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.includedirs = ["include/raul-2"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "raul")
        self.cpp_info.set_property("cmake_target_name", "raul::raul")
        self.cpp_info.set_property("pkg_config_name", "raul-2")
