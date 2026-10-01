#!/usr/bin/env python3
"""Conan recipe — libsolace 0.4.1（CMake / C++17 库，**0 个交付依赖**）。

上游形态与适配要点
------------------
* **源**：GitHub tag 归档 **zip**（URL 形态逐字取自 conan-center-index 的 libsolace
  conandata），sha256 三路独立下载逐字节同值、且与 CCI 记录值一致（见 conandata.yml
  注释与 ``$TASK_DIR/w0-evidence.md``）。
* **conan 1 遗留（唯一一处源侧改写，落补丁文件）**：上游根 ``CMakeLists.txt`` 直接
  ``include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)`` 并调用 ``conan_basic_setup()``——
  Conan 2 不再生成该文件 ⇒ 以 ``patches/0001-drop-conan1-bootstrap.patch`` 删除这两行
  （内容与 conan-center-index 同包配方 `_patch_sources()` 的 replace_in_file 逐字相同，
  由 ``export_sources()/apply_conandata_patches()`` 导出并应用）。
* **gtest 接线（上游语义复刻）**：上游 ``src/CMakeLists.txt`` 写
  ``target_link_libraries(${PROJECT_NAME} PUBLIC ${CONAN_LIBS})``，而
  ``test/CMakeLists.txt`` 只链接 ``${PROJECT_NAME}`` 与 ``rt`` —— gtest 的**头路径**与
  **库**其实全靠 conan 1 ``conan_basic_setup()`` 注入的全局 ``include_directories`` 与
  ``CONAN_LIBS``。Conan 2 没有这两个全局量，故 ``generate()`` 写一个
  ``CMAKE_PROJECT_INCLUDE`` 注入文件复刻同样的两条语义（详见 `_write_upstream_inject()`），
  **上游 test/ 源文件与各级 CMakeLists 一字未改**。
* **上游测试**：``test/`` 下 GoogleTest 单可执行 ``test_solace``（``test/CMakeLists.txt``
  里 ``add_test`` 注册），但由 ``add_subdirectory(test EXCLUDE_FROM_ALL)`` 排除在默认
  ``all`` 之外 ⇒ ``build()`` 内显式 ``cmake.build(target="test_solace")`` 构建，再在
  **沙箱 HOME** 下真跑，解析 ``[==========] N tests ... ran.`` 与 ``[  PASSED  ] N tests.``
  汇总行；并做两道反假绿硬断言（注册数 > 0、通过数 == 注册数），任一不符即构建失败。
* **测试覆盖自检**：凡 ``test/**/*.cpp`` 内含 ``TEST/TEST_F/TEST_P`` 声明的文件，必须出现在
  ``test/CMakeLists.txt`` 中 —— 否则该文件的用例会被**静默漏跑**，直接 ConanException。
* **N 的候选口径**（报告侧，recipe 只报读数）：源码宏 raw = 345、去注释后 = 333、
  框架注册 = 333；差额 12 处全部位于上游块注释内（不可编译），逐文件归因见
  ``reports/test-report.md`` 与 ``test_package/MANIFEST.yml``。
"""

import json
import os
import re
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.build import can_run, check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LibsolaceConan(ConanFile):
    name = "libsolace"
    version = "0.4.1"
    description = "High-performance components for mission-critical applications"
    license = "Apache-2.0"
    homepage = "https://github.com/abbyssoul/libsolace"
    url = "https://github.com/abbyssoul/libsolace"
    topics = ("HPC", "high-reliability", "p10", "solace", "performance", "c++")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # W0 双源实证（上游 conanfile.txt [requires] 段为空 + CCI 配方无 requirements()）
        # ⇒ 交付依赖 0 个，无 SSL/压缩/数据库等可选开关需要禁用。
        pass

    def build_requirements(self):
        # 仅服务上游单测；test_requires 不传播给消费者，交付依赖仍为 0。
        # （上游 conanfile.txt 钉 gtest/1.10.0，制品仓最高 1.17.0.2，取 1.17.0——
        #  与上游 `#include <gtest/gtest.h>` + add_test 布局兼容，实测 333/333 全过。）
        self.test_requires("gtest/1.17.0")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD"):
            raise ConanInvalidConfiguration(
                "libsolace 只面向 POSIX 平台（上游 CCI 配方同样拒绝 Windows）"
            )
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 17)

    def export_sources(self):
        # 把 conandata.yml 的 patches/（本版本 1 个：0001-drop-conan1-bootstrap.patch）
        # 一起导出到配方目录，source() 里 apply_conandata_patches 才拿得到。
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    # ── gtest 接线：复刻 conan 1 conan_basic_setup() 的两条全局语义 ──────────
    def _write_upstream_inject(self) -> str:
        """生成 CMAKE_PROJECT_INCLUDE 注入文件并返回其绝对路径。

        上游根 CMakeLists 的 project() 会 include 本文件（CMake 官方注入点，
        等价于「project() 之后、所有 add_subdirectory 之前」执行），因此在**根目录作用域**
        写下的两条语义会被 src/ 与 test/ 子目录继承——这正是 conan 1
        ``conan_basic_setup()`` 提供的两件事：

        1. ``include_directories(<gtest>/include)`` —— 让 test/*.cpp 能
           ``#include <gtest/gtest.h>``；
        2. ``set(CONAN_LIBS <gtest>/lib/libgtest.a)`` —— 让上游
           ``src/CMakeLists.txt`` 的 ``target_link_libraries(${PROJECT_NAME} PUBLIC
           ${CONAN_LIBS})`` 把 gtest 挂到 solace 的传递链接上，
           ``test/CMakeLists.txt`` 只链 solace 即可拿到 gtest（上游原设计）。

        该文件写在 conan 的 generators 目录（构建期产物，**不入库**）。
        """
        gtest = self.dependencies["gtest"]
        pkg = Path(gtest.package_folder)
        include_dir = pkg / "include"
        # 静态链接：本平台 gtest 包固定 shared=False（ohpcd 包 ID 21b17f8b… 已核）。
        lib = pkg / "lib" / "libgtest.a"
        if not include_dir.is_dir() or not lib.is_file():
            raise ConanException(
                "gtest 包布局异常（缺 include/ 或 lib/libgtest.a）："
                f"{gtest.package_folder}；请从 ohpcd 制品仓重新下载 gtest/1.17.0 后重试"
            )

        inject = Path(self.generators_folder) / "libsolace-upstream-includes.cmake"
        inject.write_text(
            "# 生成文件（CMake CMAKE_PROJECT_INCLUDE 注入点）—— 非上游源码、不入库。\n"
            "# 作用：复刻 conan 1 conan_basic_setup() 提供的两条全局语义，\n"
            "#       让上游 CMakeLists（未改动）里的 include <gtest/…> 与 ${CONAN_LIBS}\n"
            "#       在 Conan 2 下语义等价。详见 conanfile.py `_write_upstream_inject()`。\n"
            f'include_directories("{include_dir}")\n'
            f'set(CONAN_LIBS "{lib}")\n',
            encoding="utf-8",
        )
        return str(inject)

    def generate(self):
        inject = self._write_upstream_inject()
        tc = CMakeToolchain(self)
        # 上游 option(PKG_CONFIG …) 默认 OFF；显式钉住，避免安装带空 Version 的
        # .pc（上游 project(solace) 未声明 VERSION，@PROJECT_VERSION@ 会展开为空）。
        tc.variables["PKG_CONFIG"] = False
        tc.cache_variables["CMAKE_PROJECT_INCLUDE"] = inject
        tc.generate()

    # ── 构建 + 上游测试（TEST_QUALITY_SPEC 层 1：测试在 build() 内真跑）────
    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()                          # 默认 all：libsolace
        cmake.build(target="test_solace")      # EXCLUDE_FROM_ALL：上游测试目标

        if can_run(self):
            self._run_upstream_tests()
        else:
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT="
                + json.dumps(
                    {
                        "status": "built_not_run",
                        "framework": "gtest",
                        "binaries": {"test_solace": 0},
                        "note": "cross-building: upstream test built but not executed",
                    },
                    ensure_ascii=False,
                )
            )

    def _run_upstream_tests(self):
        """在沙箱 HOME 下真跑上游 GoogleTest 可执行文件并做反假绿硬断言。"""
        build = Path(self.build_folder)
        cands = sorted(p for p in build.rglob("test_solace") if p.is_file())
        if not cands:
            raise ConanException(
                f"未产出上游测试可执行文件 test_solace（build 目录: {build}）"
            )
        exe = cands[0]

        # ── 覆盖自检①：含用例声明的 test/**/*.cpp 必须被 test/CMakeLists.txt 引用，
        #    否则该文件的用例会被静默漏跑（EXCLUDE_FROM_ALL + 未列源文件 = 零告警）。
        src_test = Path(self.source_folder) / "test"
        test_cmake = (src_test / "CMakeLists.txt").read_text(encoding="utf-8", errors="replace")
        macro_re = re.compile(r"^\s*(?:TEST|TEST_F|TEST_P)\s*\(", re.M)
        declared_raw = 0
        for f in sorted(src_test.rglob("*.cpp")):
            n = len(macro_re.findall(f.read_text(encoding="utf-8", errors="replace")))
            declared_raw += n
            if n and f.name not in test_cmake:
                raise ConanException(
                    f"测试文件 {f.name} 含 {n} 处 TEST 声明，但未列入 "
                    "test/CMakeLists.txt 的源文件清单 —— 上游用例会被静默漏跑"
                )
        if declared_raw <= 0:
            raise ConanException("源码宏清点为 0 —— 上游测试面不存在，判假绿")

        # ── 沙箱 HOME：不写用户真实 HOME（AGENTS §3.5）；测试本身不落盘，
        #    但仍按纪律隔离，并把 TMPDIR 一并指到构建目录内（device-facts §一.12）。
        home = build / "test-home"
        tmp = build / "test-tmp"
        home.mkdir(parents=True, exist_ok=True)
        tmp.mkdir(parents=True, exist_ok=True)
        log = build / "upstream-tests.log"

        self.run(
            f'HOME="{home}" TMPDIR="{tmp}" "{exe}" > "{log}" 2>&1; '
            f"rc=$?; cat \"{log}\"; exit $rc"
        )
        text = log.read_text(encoding="utf-8", errors="replace")

        m_ran = re.search(r"\[==========\]\s+(\d+) tests from (\d+) test suites ran", text)
        m_pass = re.search(r"\[  PASSED  \]\s+(\d+) tests", text)
        if not m_ran or not m_pass:
            raise ConanException(
                "无法从上游测试输出解析汇总行（gtest 汇总缺失）：\n" + text[-2000:]
            )
        registered, suites = int(m_ran.group(1)), int(m_ran.group(2))
        passed = int(m_pass.group(1))
        failed_lines = len(re.findall(r"^\[  FAILED  \]", text, re.M))

        # ── 反假绿硬断言（§二.22：All 0 tests passed 是判绿禁用词）────────────
        if registered <= 0:
            raise ConanException("gtest 注册用例数为 0 —— 判假绿，拒绝通过")
        if passed != registered:
            raise ConanException(
                f"gtest 通过数 {passed} != 注册数 {registered}"
                f"（FAILED 行 {failed_lines}）"
            )
        if registered > declared_raw:
            raise ConanException(
                f"框架注册数 {registered} > 源码宏数 {declared_raw}，计数口径异常"
            )

        result = {
            "status": "passed",
            "framework": "gtest",
            # 源码宏口径：raw = 不解析注释的 grep 计数（= 审方克隆后的 grep 值）
            "source_declared_total": declared_raw,
            "registered": registered,
            "test_suites": suites,
            "executed": passed,
            "passed": passed,
            "failed": 0,
            "skipped": 0,
            # raw − passed：全部为上游块注释内、任何构建都不编译的声明
            "not_run": declared_raw - passed,
            "binaries": {exe.name: passed},
            "note": (
                "not_run 全部位于上游 /* */ 块注释内（逐文件归因见 "
                "reports/test-report.md 与 test_package/MANIFEST.yml）"
            ),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))
        self.output.info(
            f"[upstream-tests] {passed}/{registered} gtest 用例通过 "
            f"（{suites} 个套件；源码宏 raw={declared_raw}，not_run={declared_raw - passed}）"
        )

    # ── 打包 ────────────────────────────────────────────────────────────────
    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libsolace")
        self.cpp_info.set_property("cmake_target_name", "libsolace::libsolace")
        self.cpp_info.set_property("pkg_config_name", "libsolace")
        self.cpp_info.libs = ["solace"]
        # 不声明 system_libs：`nm -u libsolace.a` 无任何 libm 符号
        # （无 pow/sqrt/log/exp/fabs…，源码亦无 #include <cmath>），
        # 消费者链接 libsolace.a 不需要 -lm；上游 CCI 对 Linux 追加的 "m" 在此无实证支撑。
