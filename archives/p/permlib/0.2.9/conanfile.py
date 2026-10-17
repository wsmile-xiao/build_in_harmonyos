#!/usr/bin/env python3
"""Conan recipe for permlib 0.2.9 — C++ header-only library for permutation computations.

permlib 是**纯头文件**模板库（include/permlib/**，84 个头文件）：置换群的 BSGS
数据结构、轨道/稳定化子/集合像/字典序最小集合搜索等组合算法。上游 v0.2.9 是
轻量 tag，指向 master 提交 2b4e468e24a059e3659bc095293df0cd363a22f5。

本配方的三个要点：

1. header-only ⇒ ``package_type = "header-library"``、``package_id`` 清空，
   ``package()`` 只装 ``include/permlib/**`` 与 LICENSE（无可加载产物）。

2. 公开头**直接** ``#include <boost/...>``（84 个公共头里 47 个，用到
   boost::shared_ptr / dynamic_bitset / foreach / counting_iterator 等）⇒ boost 是
   **接口依赖**，消费者编译 permlib 头时必须有 boost 头。因此：
   ``requires("boost/...")`` + ``cpp_info.requires = ["boost::headers"]``。
   必须指向 boost 的 **components["headers"]**：boost 配方声明了 components 之后，
   包级目标（boost::boost）的 include 目录为空 —— 只靠 transitive_headers 传递包级
   目标会让消费者 ``#include <boost/...>`` 直接找不到头（先例
   archives/l/liborigin2/20110117/conanfile.py 的实测结论）。

3. 上游测试是可运行的（test/*.cpp → 13 个 Boost.Test 可执行文件 / 59 个 test case），
   在 ``build()`` 里用配方自带的 ``files/CMakeLists.txt`` 编译、由 ctest 真实执行，
   语料 ``data/G_*`` 一并拷入构建根目录。header-only 包没有任何可加载产物，
   这是唯一能证明「交付的头文件真的能编译、真的能算出正确结果」的自动证据。
   上游自带的 test/CMakeLists.txt 用 legacy 变量 ${Boost_UNIT_TEST_FRAMEWORK_LIBRARY}
   链接 Boost.Test，而 Conan 生成的 BoostConfig.cmake 只提供 imported target，
   因此这里用自带的等价驱动（**不修改任何上游源文件**，13 个 .cpp 一字未改）。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class PermlibConan(ConanFile):
    name = "permlib"
    version = "0.2.9"
    description = ("C++ header-only template library for permutation computations: "
                   "BSGS data structures, orbit/stabilizer computation, "
                   "set image and lexicographically minimal set search")
    license = "BSD-3-Clause"
    homepage = "https://github.com/tremlin/PermLib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("permutation-group", "bsgs", "combinatorics", "header-only")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        # 配方自带的测试驱动（不是上游文件，见类文档第 3 点）
        copy(self, "CMakeLists.txt",
             src=os.path.join(self.recipe_folder, "files"),
             dst=os.path.join(self.export_sources_folder, "files"))
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        # 公开头依赖 boost 头 ⇒ 公开依赖；组件级传递见 package_info()/cpp_info.requires。
        self.requires("boost/1.90.0.4.1", transitive_headers=True, transitive_libs=False)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # 用 tc.variables 而不是 tc.cache_variables：cache_variables 只进
        # CMakePresets/命令行，不进 conan_toolchain.cmake —— 上游在 project()
        # 之前读会静默退化成 fallback（本仓 liblsl 任务实测）。
        tc.variables["PERMLIB_SOURCE_DIR"] = self.source_folder.replace("\\", "/")
        if self.settings.os in ("Linux", "OHOS"):
            # OHOS profile 会把 CMAKE_SYSTEM_NAME 设成 HarmonyOS，而本机 CMake 没有
            # Platform/HarmonyOS-Initialize.cmake ⇒ UNIX 变量不存在、RPATH 逻辑整支跳过。
            # 本包在 build() 里要真的跑链接了共享 boost 测试库的可执行文件，走 Linux
            # 平台模块才能拿到正确的 build RPATH（本仓 header-only 先例：array-hash 0.7.2）。
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    @staticmethod
    def _bounded_jobs(jobs):
        """本机 affinity 只有 8 路而 conan 默认取 cpu_count()=20；配方自限，避免超订。"""
        try:
            value = int(jobs)
        except (TypeError, ValueError):
            value = 2
        return max(1, min(value, 4))

    def build(self):
        apply_conandata_patches(self)
        jobs = self._bounded_jobs(self.conf.get("tools.build:jobs", default=2, check_type=int) or 2)
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.export_sources_folder, "files"))
        cmake.build(build_tool_args=["-j{}".format(jobs)])
        # 上游用例的真实执行（13 个 Boost.Test 可执行文件，ctest 注册）
        self.run("ctest --output-on-failure -j{}".format(jobs), cwd=self.build_folder)

    def package(self):
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=True)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "permlib")
        self.cpp_info.set_property("cmake_target_name", "permlib::permlib")
        # 组件级传递（见类文档第 2 点）：包级 boost::boost 无 include 目录。
        self.cpp_info.requires = ["boost::headers"]
