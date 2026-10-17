#!/usr/bin/env python3
"""Conan recipe — platform.equality 0.0.1 (CMake)

Platform.Equality 是 linksplatform 的 C++20 头文件库，为 `std::any` 提供
运行期类型分派的相等比较（`std::any == std::any`），并为 `std::ranges::range`
提供 `std::equal_to` 偏特化（按元素逐位比较）。

--- 上游状态与 OHOS 适配要点 -----------------------------------------------

1. 本库是 **header-only**（`Platform.Equality/` 下的 4 个头文件，CMake 里是
   `add_library(... INTERFACE)`），没有可编译产物，但**上游带完整单测**
   （`cpp/Platform.Equality.Tests/Platform.Equality.Tests.cpp`，5 个 TEST）。

2. 上游 `Platform.Equality.Tests/CMakeLists.txt` 用
   `FetchContent_Declare(googletest URL https://github.com/google/googletest/...)`
   在 configure 期从 GitHub 拉 googletest 源码。
   - GitHub 在 OHOS CI 环境不可达，configure 必然挂；
   - 这属于"网络构建"，违反仓库"依赖走 Conan 制品仓"的约定。
   因此**不用上游的 `.Tests` 子工程**，改为在本配方里用 Conan 的 `gtest`
   重新编译同一份上游测试源文件（`patches/` 不改测试代码，只加构建胶水），
   保持"跑真实上游测试"的语义（R51/R4）。

3. OHOS SDK 自带 libc++ 把 `<ranges>` 里的算法（`std::ranges::equal` 等）默认
   关在 `_LIBCPP_HAS_NO_INCOMPLETE_RANGES` 后面 —— 该宏由 **没有**
   `-D_LIBCPP_ENABLE_EXPERIMENTAL` 时的默认配置打开。表现是：
       Platform.Equality.Range.h:18:20: error: no member named 'equal' in
           namespace 'std::ranges'; did you mean simply 'equal'?
   本库 `Range.h` 的核心实现就依赖 `std::ranges::equal`，必须打开该宏。

4. `Platform.Equality.Any.h` 的 include 不自洽：用了 `std::string` 与
   `std::unordered_map` 却没 include 对应头。GCC 上靠 `<gtest/gtest.h>`
   传递包含侥幸编过，OHOS libc++ 上直接报
   `implicit instantiation of undefined template 'std::basic_string<char>'`。
   用补丁补齐 include（见 patches/）。
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
import os

required_conan_version = ">=2.0"


class PlatformEqualityConan(ConanFile):
    name = "platform.equality"
    version = "0.0.1"
    package_type = "header-library"

    description = ("C++20 equality library: runtime-dispatched std::any comparison "
                   "and std::ranges::range std::equal_to specialization")
    homepage = "https://github.com/linksplatform/Equality"
    license = "MIT"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    options = {"build_tests": [True, False]}
    default_options = {"build_tests": True}

    exports_sources = "patches/*", "CMakeLists.txt"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "CMakeLists.txt", src=self.recipe_folder, dst=self.export_folder)

    def source(self):
        # 上游是 .zip 包（tag 0.0.1），strip_root 去掉 Equality-0.0.1/ 前缀。
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def layout(self):
        cmake_layout(self)

    def build_requirements(self):
        # 仅测试用；header-only 库本体零依赖（消费者依赖图不含 gtest）。
        # 放在 build_requirements() 而非 requirements()：test_requires 语义等价
        # 于构建期需求，与仓库先例 x86-simd-sort/5.0 一致。
        if self.options.build_tests:
            self.test_requires("gtest/1.17.0")

    def generate(self):
        # 不用上游 cpp/CMakeLists.txt：它会在 configure 期 FetchContent 拉
        # googletest（GitHub 不可达）。这里直接编译上游测试源 + Conan 的 gtest。
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        if self.settings.os == "OHOS":
            # OHOS libc++ 默认关掉 <ranges> 算法（见文件头第 3 点）。
            # 用 extra_cxxflags 追加：CMAKE_CXX_FLAGS 由 CMakeToolchain 统一管理，
            # 手工赋值会覆盖 toolchain/profile 已经组装好的内容（同一先例：
            # archives/p/plutobook/0.19.0、archives/m/mrc/1.3.17 均为同一 libc++ 缺口）。
            tc.extra_cxxflags.append("-D_LIBCPP_ENABLE_EXPERIMENTAL")
        tc.generate()
        # CMakeLists.txt 用 find_package(gtest REQUIRED CONFIG)，gtest-config.cmake
        # 由 CMakeDeps 生成（CMakeToolchain 不产出）。缺了它 CMake 会回退到内置
        # FindGTest.cmake 去找系统/sysroot 的 gtest，使 test_requires("gtest/1.17.0")
        # 的 pin 形同虚设。
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        if not self.options.build_tests:
            return
        cmake = CMake(self)
        # build_script_folder 默认是 source_folder；配方自带的 CMakeLists.txt
        # 通过 exports_sources 落到 source_folder，与上游源码同级。
        cmake.configure()
        cmake.build()
        # 真实执行上游测试套件（5 个 TEST 用例 / 15 条断言）。
        # 交叉编译下由 profile 的 CMAKE_CROSSCOMPILING_EMULATOR(qemu) 执行。
        cmake.test()

    def package(self):
        # header-only：把 4 个公共头装到 include/。
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "cpp", "Platform.Equality"),
             dst=os.path.join(self.package_folder, "include"))
        # P3-2：LICENSE* 若匹配不到会静默产出空 licenses/ 目录。
        # header-library 的 package_type 不会因此报错，故显式校验。
        copied = copy(self, "LICENSE*", src=self.source_folder,
                      dst=os.path.join(self.package_folder, "licenses"))
        if not copied:
            raise ConanException(
                "LICENSE* not found in upstream source (expected at repo root); "
                "refusing to ship an empty licenses/ directory."
            )

    def package_id(self):
        # 纯头文件库：产物与编译器/构建类型无关。
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        # P1（本地检视第 2 轮）：本库是 header-only，`-D_LIBCPP_ENABLE_EXPERIMENTAL`
        # 真正生效的位置是**消费者的 TU**（Range.h 依赖 std::ranges::equal，
        # 而 OHOS libc++ 默认以 _LIBCPP_HAS_NO_INCOMPLETE_RANGES 裁剪该算法族）。
        # 只在 generate() 里给自己加是不够的 —— 必须随包导出，否则任何消费者
        # 只要用到 Range.h 就会报：
        #   Platform.Equality.Range.h:19:20: error: no member named 'equal'
        #       in namespace 'std::ranges'
        # 已实测：未导出时消费者编译失败，导出后编译通过。
        if self.settings.os == "OHOS":
            self.cpp_info.defines.append("_LIBCPP_ENABLE_EXPERIMENTAL")
        # 包名带点（platform.equality），显式声名 CMake target，避免消费者端
        # 生成的名字与 find_package(platform.equality) 对不上。
        self.cpp_info.set_property("cmake_file_name", "platform.equality")
        self.cpp_info.set_property("cmake_target_name",
                                   "platform.equality::platform.equality")
