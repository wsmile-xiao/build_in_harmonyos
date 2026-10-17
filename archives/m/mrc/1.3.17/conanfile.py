#!/usr/bin/env python3
"""Conan recipe — mrc 1.3.17 (CMake, C++20).

mrc = resource compiler：把二进制资源编译成目标文件（.obj），供 C++ 程序内嵌。
hekkelman 工具链组件，cif-tools 2.0.0 通过 find_package(mrc) **可选**使用
（找不到则 USE_RSRC=FALSE，仅关闭资源功能）。

OHOS adaptation notes：
- **mcfp 依赖**：上游用 `CPMAddPackage("https://forge.hekkelman.net/maarten/mcfp.git@1.4.1")`
  （非 GitHub 域名，CI 禁网）。本配方改为 conan 依赖 `libmcfp`，并在 generate()
  把 `mcfp_DIR` 指向包内的上游 config 目录（`lib/cmake/mcfp`）——上游 CMakeLists 已设
  `CPM_USE_LOCAL_PACKAGES ON`，CPMAddPackage 会先尝试 find_package(mcfp)，
  命中即不再联网下载。
  注意：**包名与 CMake 名不同**——conan 包名是 libmcfp，而上游导出的 CMake 包名/
  target 是 `mcfp` / `mcfp::mcfp`，故不能只靠 CMakeDeps 生成的
  `libmcfp-config.cmake`，必须用 mcfp_DIR 显式指向上游 config。
- **BUILD_TESTING=OFF（默认）**：上游单元测试（9 个 TEST_CASE / 32 assertions）经
  `CPMAddPackage("gh:catchorg/Catch2@3.5.0")` 拉取，CI 沙箱禁网。
  但上游 CMakeLists 在 `CPMAddPackage` 之前设了 **`CPM_USE_LOCAL_PACKAGES ON`**
  → CPM 会**先尝试 `find_package(<name>)`**，命中即不再联网。
  故本配方提供门控 option `run_upstream_tests`：开启时用 `test_requires("catch2/3.8.1")`
  并把 **`Catch2_DIR`** 指向包内上游 config（`lib/cmake/Catch2`），即可**离线**满足 CPM，
  **无需 patch 上游 CMakeLists**。实测开启后 `CMake configure` 输出
  `-- CPM: Using local package Catch2@3.8.1`，9/9 test cases 全通过（32 assertions）。
- `endian.h`：OHOS sysroot 提供，`LITTLE_ENDIAN` 宏可用（aarch64 little-endian，
  mrc.cpp 的 `#if defined(LITTLE_ENDIAN)` 分支正确命中）。
- 构建期 `add_custom_command` 会运行自建的 mrc-bootstrap 工具生成 .obj ——
  OHOS 设备可执行 aarch64 本机二进制，实测通过。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches


class MrcConan(ConanFile):
    name = "mrc"
    version = "1.3.17"
    description = "mrc — resource compiler, embeds binary resources into object files"
    license = "BSD-2-Clause"
    homepage = "https://forge.hekkelman.net/maarten/mrc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    # 门控上游测试：默认关闭以保持交付包无测试依赖（catch2 仅 test_requires 注入）
    options = {"run_upstream_tests": [True, False]}
    default_options = {"run_upstream_tests": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # header-only C++20 命令行解析库（mrc 用它解析参数）
        self.requires("libmcfp/1.4.2", transitive_headers=True, transitive_libs=True)
        # 上游测试框架：仅 test_requires，不进入交付包的依赖（门控关闭时更不参与）
        if self.options.run_upstream_tests:
            self.test_requires("catch2/3.8.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dep_config_dir(self, dep, rel_paths, marker):
        """在依赖包内定位上游 CMake config 目录（按 marker 文件判定）。

        注意：conan 包名与上游 CMake 包名**未必一致**，故不依赖 CMakeDeps 生成的
        config，而是直接用包内**上游自带**的 config 目录。
        """
        pf = dep.package_folder
        if not pf:
            return None
        for rel in rel_paths:
            cand = os.path.join(pf, *rel)
            if os.path.isfile(os.path.join(cand, marker)):
                return os.path.abspath(cand)
        return None

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 上游测试默认关闭（CPM 拉 Catch2 需联网）；开启时用下方 Catch2_DIR 离线满足
        tc.variables["BUILD_TESTING"] = "ON" if self.options.run_upstream_tests else "OFF"
        # 【OHOS 关键】恢复 std::ranges 算法：libc++15 的 __config 在
        # !_LIBCPP_ENABLE_EXPERIMENTAL && !_LIBCPP_BUILDING_LIBRARY 时定义
        # _LIBCPP_HAS_NO_INCOMPLETE_RANGES，导致 std::ranges::copy 等算法不存在
        # （实测 mrc.cpp:929/964 报 'no member named copy in namespace std::ranges'）。
        # ranges 为 header-only 模板，开启后编译/链接/运行均通过
        # （libcifpp 10.0.4 配方同款）。
        for flag_list in (tc.extra_cxxflags, tc.extra_cflags):
            if "-D_LIBCPP_ENABLE_EXPERIMENTAL" not in flag_list:
                flag_list.append("-D_LIBCPP_ENABLE_EXPERIMENTAL")
        # mcfp：把 mcfp_DIR 指向依赖包内的上游 config 目录
        # （上游 CPM_USE_LOCAL_PACKAGES=ON → CPMAddPackage 先 find_package(mcfp)）
        for _n, dep in self.dependencies.items():
            pf = dep.package_folder
            if not pf:
                continue
            for cand in (os.path.join(pf, "lib", "cmake", "mcfp"),
                         os.path.join(pf, "share", "cmake", "mcfp"),
                         os.path.join(pf, "lib", "cmake"),
                         os.path.join(pf, "share", "cmake")):
                if os.path.isfile(os.path.join(cand, "mcfpConfig.cmake")):
                    tc.variables["mcfp_DIR"] = os.path.abspath(cand)
                    break
            if "mcfp_DIR" in tc.variables:
                # 依赖 include 注入（mcfp 是 header-only，靠 -I 可见）
                for p in dep.cpp_info.includedirs:
                    f = "-I" + p
                    if f not in tc.extra_cxxflags:
                        tc.extra_cxxflags.append(f)
        # Catch2：同样经 CPM_USE_LOCAL_PACKAGES 走本地包 → 只需给出 Catch2_DIR。
        # 注意 catch2 的 conan 名与 CMake 包名不同大小写（catch2 vs Catch2），
        # 且 config 位于 lib/cmake/Catch2（大写），故按 marker 定位而非拼包名。
        if self.options.run_upstream_tests:
            for _n, dep in self.dependencies.items():
                d = self._dep_config_dir(dep, [("lib", "cmake", "Catch2"),
                                               ("share", "cmake", "Catch2")],
                                         "Catch2Config.cmake")
                if d:
                    tc.variables["Catch2_DIR"] = d
                    self.output.info(f"mrc: upstream tests ON, Catch2_DIR={d}")
                    break
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # BUILD_TESTING=ON 时 mrc-unit-test 属 ALL 目标（上游 add_executable），
        # 故一次 cmake.build() 即同时构建 mrc 与测试可执行文件
        cmake.build()
        if self.options.run_upstream_tests:
            # 实跑上游单元测试（9 个 TEST_CASE / 32 assertions）。
            # 注意（E301）：Conan 2 的 CMake.test(cli_args=…) 会把参数路由给
            # `cmake --build --target test`，故 ctest 选项（如 --output-on-failure）
            # 必须走 **CMake.ctest()** —— 这是 ctest 的专用助手，否则报
            # "Unknown argument --output-on-failure"。
            cmake.ctest(cli_args=["--output-on-failure"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        # cif-tools 用 find_package(mrc) 且需要 MRC_EXECUTABLE / mrc_write_header
        # ——上游 config 名即 mrc，对齐之
        self.cpp_info.set_property("cmake_file_name", "mrc")
