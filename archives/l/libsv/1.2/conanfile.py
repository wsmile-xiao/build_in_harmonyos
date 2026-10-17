#!/usr/bin/env python3
"""Conan recipe — libsv 1.2 (CMake)"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, save


class LibsvConan(ConanFile):
    name = "libsv"
    version = "1.2"
    description = "Public domain cross-platform semantic versioning in C99"
    license = "Unlicense"
    homepage = "https://github.com/uael/sv"
    url = "https://github.com/uael/sv"
    topics = ("semver", "semantic-versioning", "version", "parser")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": True,
    }

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # os=OHOS 由适配版 conan 自动映射 CMAKE_SYSTEM_NAME=HarmonyOS 并
        # 注入工具链环境；不再手动别名 Linux（旧 workaround 会绕开 conan
        # 的 OHOS 处理链，导致真机 PATH 缺 /data/service/hnp/bin 找不到
        # cmake，实测 r1 轮 exit 127）。
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if not cross_building(self):
            self._run_upstream_tests()
        else:
            # 交叉构建宿主机无法执行目标架构二进制；真机/CI 为 OHOS 原生
            # 构建（非交叉），上游 ctest 仍会完整执行。
            self.output.info(
                "Cross-building: skipping upstream test run "
                "(target binaries cannot execute on this host)"
            )

    def _run_upstream_tests(self):
        # 上游 7 个 ctest 程序：comp/match/range/semvers/usage/utils/version。
        # OHOS 构建树产物无 rpath，musl 加载器需要 LD_LIBRARY_PATH 指向
        # 构建输出目录；而 self.run 的 shell 级变量前缀会被 conan 的环境
        # 管理剥离（profile [buildenv] 注册了同名变量），故生成包装脚本
        # 在其内部 export——脚本内部设置不受 conan 环境管理影响
        # （真机实测该方式 ctest 7/7 通过）。
        # cmake_layout 下 self.build_folder 即二进制输出目录（build/Release），
        # libsv.so 与测试程序同在该目录；对多配置布局差异做存在性兜底。
        lib_dir = self.build_folder
        if not os.path.isfile(os.path.join(lib_dir, "libsv.so")):
            fallback = os.path.join(self.build_folder, "build", "Release")
            if os.path.isfile(os.path.join(fallback, "libsv.so")):
                lib_dir = fallback
        log_path = os.path.join(self.build_folder, "upstream-ctest.log")
        script = os.path.join(self.build_folder, "run-upstream-ctests.sh")
        save(
            self,
            script,
            "#!/bin/sh\n"
            'LD_LIBRARY_PATH="%s" ctest --test-dir "%s" --output-on-failure'
            ' > "%s" 2>&1\n'
            "exit $?\n" % (lib_dir, self.build_folder, log_path),
        )
        error = None
        try:
            self.run('sh "%s"' % script)
        except Exception as exc:
            error = exc

        output = ""
        if os.path.isfile(log_path):
            with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
                output = handle.read()
            self.output.info("Upstream CTest output:\n%s" % output)

        passed = output.count("   Passed")
        expected = 7
        result = {
            "status": "passed" if error is None and passed == expected else "failed",
            "framework": "CTest",
            "command": "ctest --test-dir <build> --output-on-failure",
            "discovered": expected,
            "executed": expected if error is None else 0,
            "passed": passed,
            "failed": expected - passed if error is None else expected,
            "skipped": 0,
        }
        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result)
        print(marker, flush=True)
        self.output.info(marker)
        if error is not None:
            raise ConanException("upstream CTest failed: %s" % error)
        if passed != expected:
            raise ConanException(
                "upstream CTest evidence mismatch: expected %d passed, got %d"
                % (expected, passed)
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "UNLICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["sv"]
        self.cpp_info.set_property("cmake_file_name", "libsv")
        self.cpp_info.set_property("cmake_target_name", "libsv::libsv")
        self.cpp_info.set_property("pkg_config_name", "libsv")
