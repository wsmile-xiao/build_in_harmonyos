#!/usr/bin/env python3
"""Conan recipe — CRCpp 1.2.1.0 (header-only C++ CRC library).

CRC++ 是单头文件（inc/CRC.h）header-only C++ 库，零依赖、无编译产物：
- package_type = "header-library" + implements auto_header_only_mode；
- package() 只交付 include/CRC.h 与 licenses/LICENSE；
- 上游测试面（rule4/R51）：上游 CI（.github/workflows/unit-test.yml）口径为
  `make -C test/prj/gcc` 后运行 `test/prj/gcc/bin/unittest`；上游 gcc Makefile
  的 CXXFLAGS 默认带 -DCRCPP_INCLUDE_ESOTERIC_CRC_DEFINITIONS。
  本配方 build() 在 build 目录复刻上游相对结构后驱动上游 Makefile（只覆盖
  CXX/LINKER 为设备 clang++、LDFLAGS 追加 -static-libstdc++，让测试二进制在
  无 LD_LIBRARY_PATH 的环境下可直接运行），并实际运行 unittest。
- 断言计数（ifdef 感知清点 test/src/main.cpp）：CRC_TEST 宏 ×4 断言、
  CRC_PARTIAL_BYTE_TEST ×2 断言；esoteric 开启时 59×4 + 3×2 = 242 条运行期
  断言。unittest 仅在断言失败时向 stderr 打印 "Invalid CRC" 并置
  returnCode=1，故 rc==0 且 stderr 无该行 ⇒ 242 条全部通过。
"""
import os
import re
import shutil
import signal
import subprocess

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CrcppConan(ConanFile):
    name = "crcpp"
    version = "1.2.1.0"
    description = "CRC++ — header-only single-header C++ library for CRC calculation (bit-by-bit, table-driven, multipart, arbitrary width)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/d-bahr/CRCpp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "header-library"
    implements = ["auto_header_only_mode"]

    settings = "os", "compiler", "build_type", "arch"

    # header-only：源码只读，build()/package() 直接从 source_folder 读取
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # ── 上游测试集成（R51 上游测试三步法）────────────────────────────────
    def build(self):
        apply_conandata_patches(self)
        self._run_upstream_tests()

    def _run_cmd(self, cmd, cwd=None, timeout=600):
        """带超时与独立会话的命令执行（防孤儿编译进程占用设备）。"""
        proc = subprocess.Popen(
            cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, stdin=subprocess.DEVNULL,
            start_new_session=True)
        try:
            out, err = proc.communicate(timeout=timeout)
            return proc.returncode, out, err
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()
            out, err = proc.communicate()
            return -1, out, err

    @staticmethod
    def _count_upstream_assertions(main_cpp):
        """ifdef 感知清点上游测试断言数（候选数法的断言口径）。

        CRC_TEST 展开 4 条断言（bit-by-bit / partial bit-by-bit / table /
        partial table），CRC_PARTIAL_BYTE_TEST 展开 2 条（非 8 位整倍数输入的
        bit-by-bit + table）。#ifdef CRCPP_INCLUDE_ESOTERIC_CRC_DEFINITIONS
        区段内的用例仅在定义该宏时参与。
        """
        common_crt = eso_crt = common_part = eso_part = 0
        cond_stack = []
        with open(main_cpp, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                stripped = line.lstrip()
                if stripped.startswith("#ifdef CRCPP_INCLUDE_ESOTERIC_CRC_DEFINITIONS"):
                    cond_stack.append("eso")
                    continue
                if stripped.startswith("#if"):
                    cond_stack.append("other")
                    continue
                if stripped.startswith("#else"):
                    continue
                if stripped.startswith("#endif"):
                    if cond_stack:
                        cond_stack.pop()
                    continue
                esoteric = "eso" in cond_stack
                if re.match(r"^\s+CRC_TEST\(", line):
                    if esoteric:
                        eso_crt += 1
                    else:
                        common_crt += 1
                elif re.match(r"^\s+CRC_PARTIAL_BYTE_TEST\(", line):
                    if esoteric:
                        eso_part += 1
                    else:
                        common_part += 1
        with_esoteric = (common_crt + eso_crt) * 4 + (common_part + eso_part) * 2
        without = common_crt * 4 + common_part * 2
        detail = {
            "crt_total": common_crt + eso_crt,
            "crt_common": common_crt,
            "crt_esoteric": eso_crt,
            "part_total": common_part + eso_part,
            "with_esoteric": with_esoteric,
            "without_esoteric": without,
        }
        return with_esoteric, without, detail

    def _run_upstream_tests(self):
        """上游 CI 同口径：make -C test/prj/gcc → test/prj/gcc/bin/unittest。

        只覆盖 CXX/LINKER（设备无 g++，显式 clang++）与 LDFLAGS（追加
        -static-libstdc++）；测试源、断言与宏定义保持上游原样。
        """
        src = self.source_folder
        main_cpp = os.path.join(src, "test", "src", "main.cpp")
        if not os.path.isfile(main_cpp):
            raise Exception(f"上游测试源缺失: {main_cpp}")

        n_with, n_without, detail = self._count_upstream_assertions(main_cpp)
        self.output.info(
            "[upstream-tests] 清点 test/src/main.cpp: "
            f"CRC_TEST={detail['crt_total']} (common {detail['crt_common']} + "
            f"esoteric {detail['crt_esoteric']}), "
            f"CRC_PARTIAL_BYTE_TEST={detail['part_total']}; "
            f"esoteric on 断言={n_with}, esoteric off 断言={n_without}")

        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")

        # 在 build 目录复刻上游 make 需要的相对结构，保持 source 目录只读
        for rel in ("inc", os.path.join("test", "src"),
                    os.path.join("test", "prj", "gcc")):
            shutil.copytree(os.path.join(src, rel),
                            os.path.join(self.build_folder, rel),
                            dirs_exist_ok=True)

        make_dir = os.path.join(self.build_folder, "test", "prj", "gcc")
        cmd_make = (
            f'make -C "{make_dir}" '
            f'CXX="{cxx}" LINKER="{cxx}" '
            f'LDFLAGS="-Wall -static-libstdc++"'
        )
        rc, out, err = self._run_cmd(cmd_make, timeout=600)
        for line in (out + err).strip().splitlines():
            self.output.info(f"[upstream-make] {line}")
        if rc != 0:
            raise Exception(f"上游 make -C test/prj/gcc 失败 rc={rc}")

        exe = os.path.join(make_dir, "bin", "unittest")
        if not os.path.isfile(exe):
            raise Exception(f"上游测试程序未生成: {exe}")
        rc, out, err = self._run_cmd(f'"{exe}"', timeout=300)
        for line in out.strip().splitlines():
            self.output.info(f"[upstream-unittest] {line}")
        for line in err.strip().splitlines():
            self.output.info(f"[upstream-unittest:stderr] {line}")
        # unittest 只在断言失败时向 stderr 打印 "Invalid CRC" 并置 returnCode=1
        failed = len([l for l in err.splitlines() if "Invalid CRC" in l])
        if rc != 0 or failed:
            raise Exception(
                f"上游 unittest 失败: rc={rc}, 失败断言={failed} "
                f"(期望 {n_with} 条全过)")
        self.output.info(
            f"[upstream-tests] RUN rc=0, stderr 无 'Invalid CRC' 行 "
            f"→ {n_with}/{n_with} 断言通过 (esoteric on, 上游 CI 同口径)")

    # ── 打包 ────────────────────────────────────────────────────────────
    def package(self):
        copy(self, "CRC.h",
             src=os.path.join(self.source_folder, "inc"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "crcpp")
        self.cpp_info.set_property("cmake_target_name", "crcpp::crcpp")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
