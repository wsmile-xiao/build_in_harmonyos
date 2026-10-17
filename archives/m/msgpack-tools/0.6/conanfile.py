#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# conanfile.py — msgpack-tools 0.6 (OpenHarmony PC 适配)
#
# 上游: https://github.com/ludocode/msgpack-tools
# 构建: CMake；mpack/rapidjson/libb64 全部内置于官方 tarball 的 contrib/ 中，
#       CMakeLists 的 EXISTS 检查保证构建期不联网下载，因此无外部 requires。
#
# 鸿蒙适配要点:
#   1. CMAKE_SYSTEM_NAME=Linux — 上游 CMake 不识别 HarmonyOS，
#      mpack 的 CMakeLists 有 STREQUAL "Linux" 分支 (知识 E092)。
#   2. CMAKE_POLICY_VERSION_MINIMUM=3.5 — CMake 4 拒绝上游
#      cmake_minimum_required(VERSION 2.6) (知识 E321)。
#   3. 上游测试 wrapper (tools/valgrind.sh, tools/test-*.sh) 的 shebang 为
#      #!/bin/bash，而鸿蒙 PC 无 /bin/bash。CTest 依赖 shell=True +
#      env=find_program(SH) 间接调用，把 sh shim 注入 PATH 即可运行全部 26 项。

import os
import re
import shutil
import subprocess
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, get


class MsgpackToolsConan(ConanFile):
    name = "msgpack-tools"
    version = "0.6"
    description = "MessagePack 与 JSON 互转的命令行工具 (msgpack2json / json2msgpack)"
    license = "MIT"
    homepage = "https://github.com/ludocode/msgpack-tools"
    url = "https://github.com/ludocode/msgpack-tools"
    topics = ("msgpack", "json", "converter", "cli")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def layout(self):
        cmake_layout(self)

    def source(self):
        # get() 校验 conandata.yml 中的 sha256 后解压;官方 release tarball
        # 顶层目录为 msgpack-tools-0.6/,strip_root=True 去掉。
        # 镜像下载由 CI pre-download (gh-proxy.com 前缀 + file:// 改写)
        # 负责,recipe 直接使用官方 URL;url 可能为 str 或 CI 改写的 list。
        entry = self.conan_data["sources"][self.version]
        url = entry["url"]
        if isinstance(url, list):
            url = url[0]
        get(self, url, sha256=entry["sha256"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 CMake 不识别 HarmonyOS;包以 clang 原生构建,不依赖
        # Linux 特有 API,故按 E092 设为 Linux。
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["BUILD_TESTING"] = True
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游 CTest 26 项 — 全量运行并统计,不得跳过
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        env = os.environ.copy()
        # --show-only 先取总数,再全量运行;退出码非 0 即失败。
        total = subprocess.run(
            ["ctest", "--show-only=json-v1"],
            cwd=self.build_folder, env=env,
            capture_output=True, text=True, check=True,
        )
        n_tests = len(re.findall(r'"command" :', total.stdout))
        self.output.info(f"upstream ctest: {n_tests} tests registered")
        run = subprocess.run(
            ["ctest", "--output-on-failure", "--output-log", "ctest-full.log"],
            cwd=self.build_folder, env=env,
            capture_output=True, text=True, errors="replace",
        )
        # ctest 正常日志尾部: "100% tests passed, 0 tests failed out of 26"
        m = re.search(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)", run.stdout)
        if run.returncode != 0 or not m or m.group(2) != "0":
            self.output.error(run.stdout[-3000:] + run.stderr[-2000:])
            raise ConanInvalidConfiguration(
                f"upstream ctest failed: rc={run.returncode}")
        self.output.success(
            f"upstream ctest: {m.group(1)}% passed, "
            f"{m.group(2)} failed, {m.group(3)} total")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            for exe in ("msgpack2json", "json2msgpack"):
                self._sign_ohos_elf(
                    os.path.join(self.package_folder, "bin", exe))

    @staticmethod
    def _sign_ohos_elf(path):
        # OHOS ELF 自签名,与 abx/0.1 同范式: binary-sign-tool 签名后
        # 校验 .codesign 段唯一,替换原文件。
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf") \
            or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(path):
            raise ConanInvalidConfiguration(f"Missing packaged executable: {path}")
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration("Required OHOS signing tool is missing")
        output = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True, timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", output],
            check=True, capture_output=True, text=True, timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanInvalidConfiguration(
                "Signed packaged executable has invalid .codesign count")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
