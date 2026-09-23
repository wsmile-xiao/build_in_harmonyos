#!/usr/bin/env python3
"""Conan recipe for openhmd 0.3.0 — Free and Open Source API and drivers
for immersive technology (VR HMDs) — pure C.

OHOS 适配要点（模式：上游 CMake 构建，零源码补丁）：
- 依赖：hidapi/0.14.0（制品仓已发布，libusb 后端，libhidapi-libusb.so）
- 上游 CMakeLists.txt 的 cmake_minimum_required(VERSION 3.1) 与 CI 的
  CMake 4.x 不兼容 —— 通过 CMAKE_POLICY_VERSION_MINIMUM=3.5 传参解决，
  无需补丁（CMake 官方推荐的对旧项目的兼容开关）
- 上游 cmake/FindHIDAPI.cmake 为 module 模式查找（find_library NAMES
  hidapi hidapi-libusb + find_path PATH_SUFFIXES hidapi）——conan CMakeDeps
  生成的是 config 模式（hidapi-config.cmake），module 与 config 不互通；
  直接注入 HIDAPI_LIBRARY/HIDAPI_INCLUDE_DIR cache 变量（上游 Find 模块
  尊重 cache 变量优先），实现零补丁消费 conan hidapi 包
- 驱动源码 #include <hidapi.h> 为平铺路径，conan hidapi 包头文件位于
  include/hidapi/hidapi.h —— FindHIDAPI 返回的 HIDAPI_INCLUDE_DIR 即为
  .../include/hidapi（find_path PATH_SUFFIXES 自动剥层），链接验证通过
- 默认静态库（R26：openhmd 与 OHOS 系统库不同名，但上游 CMake 默认
  静态 + OHMD_STATIC 宏联动导出控制，保持上游默认）
- 平台代码 platform-posix.c（pthread/clock_gettime）在 OHOS 上原生可用
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches


class OpenhmdConan(ConanFile):
    name = "openhmd"
    version = "0.3.0"
    description = "Free and Open Source API and drivers for immersive technology (VR head-mounted displays)"
    license = "BSL-1.0"
    homepage = "https://github.com/OpenHMD/OpenHMD"
    url = ""  # CI fills this

    package_type = "library"
    languages = "C"
    topics = ("vr", "hmd", "driver", "immersive")

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # R32: OHOS 与 Linux 同属 POSIX 消费面
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os} (only Linux/OHOS)"
            )

    def export_sources(self):
        # 本配方零补丁（上游源码未修改——兼容性经 CMAKE_POLICY_VERSION_MINIMUM
        # 与 HIDAPI cache 变量注入解决），保留标准结构以符合门禁 G1
        export_conandata_patches(self)

    def requirements(self):
        # 上游默认驱动集（Oculus Rift/Deepoon/WMR/HTC Vive/NOLO/3Glasses）
        # 均 find_package(HIDAPI REQUIRED) —— hidapi 是硬依赖
        self.requires("hidapi/0.14.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # 不构建上游 examples/simple（其 CMakeLists 假定构建树内链接，
        # 与 conan 分离布局不兼容；库本身的安装不依赖它）
        tc.variables["OPENHMD_EXAMPLE_SIMPLE"] = False
        # PSVR 驱动上游默认 OFF，保持上游默认
        # 其余驱动（Rift/Deepoon/WMR/Vive/NOLO/3Glasses/External/dummy）
        # 默认 ON，全部保留 —— 完整驱动集
        tc.generate()
        # 上游 FindHIDAPI（module 模式）cache 变量注入：
        # CMakeDeps 生成 hidapi-config.cmake（config 模式），上游用
        # find_package(HIDAPI)（大写 module 模式）——直接提供 cache 值，
        # 上游 Find 模块尊重已定义的 cache 变量（FPHSA 检查两变量即通过）
        hid = self.dependencies["hidapi"]
        hid_lib_dir = os.path.join(hid.package_folder, "lib")
        # conan hidapi/0.14.0 只产出 libhidapi-libusb.so（libusb 后端）
        hid_lib = os.path.join(hid_lib_dir, "libhidapi-libusb.so")
        if not os.path.exists(hid_lib):
            # 静态变体兜底（.a）
            hid_lib = os.path.join(hid_lib_dir, "libhidapi-libusb.a")
        hid_inc = os.path.join(hid.package_folder, "include", "hidapi")
        # 写入 CMakeToolchain 生成的 conan_toolchain.cmake 同目录的
        # 前置 cache 变量（通过 tc.variables 也可以，但 cache 变量必须
        # 在 toolchain 里以 set(... CACHE) 形式声明才优先于 find 逻辑）
        with open(os.path.join(self.generators_folder, "ohmd_hidapi_cache.cmake"), "w") as f:
            # 上游 cmake_minimum_required(VERSION 3.1) 与 CMake 4.x 不兼容 ——
            # 官方兼容开关（cache 变量必须出现在 -C 初始 cache 里，
            # CMAKE_POLICY_VERSION_MINIMUM 在 project() 前生效）
            f.write('set(CMAKE_POLICY_VERSION_MINIMUM "3.5" CACHE STRING "compat")\n')
            # conan toolchain 开启 CMAKE_FIND_PACKAGE_PREFER_CONFIG，上游
            # find_package(HIDAPI) 会命中 CMakeDeps 的 hidapi-config.cmake
            # （config 模式），绕过上游 FindHIDAPI.cmake（module 模式）——
            # config 文件只定义 imported target，不设置上游 CMakeLists 消费
            # 的 HIDAPI_INCLUDE_DIRS/HIDAPI_LIBRARIES 变量。四个变量全部
            # 预置（单数=FindHIDAPI 的 find_library/find_path 结果变量，
            # 复数=CMakeLists 直接消费的变量），两条路径都通
            f.write(f'set(HIDAPI_LIBRARY "{hid_lib}" CACHE FILEPATH "hidapi lib (conan)")\n')
            f.write(f'set(HIDAPI_INCLUDE_DIR "{hid_inc}" CACHE PATH "hidapi include (conan)")\n')
            f.write(f'set(HIDAPI_INCLUDE_DIRS "{hid_inc}" CACHE PATH "hidapi includes (conan)")\n')
            f.write(f'set(HIDAPI_LIBRARIES "{hid_lib}" CACHE FILEPATH "hidapi libs (conan)")\n')

    def build(self):
        # 零补丁（conandata.yml patches: {}），调用保留标准结构以符合门禁 G1
        apply_conandata_patches(self)
        cmake = CMake(self)
        # 注入 cache 变量文件（在 toolchain 之后加载）
        cmake.configure(
            cli_args=["-C", os.path.join(self.generators_folder, "ohmd_hidapi_cache.cmake")]
        )
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["openhmd"]
        self.cpp_info.set_property("cmake_file_name", "openhmd")
        self.cpp_info.set_property("cmake_target_name", "openhmd::openhmd")
        self.cpp_info.set_property("pkg_config_name", "openhmd")
        if str(self.settings.os) in ("Linux", "OHOS"):
            # platform-posix.c：pthread + clock_gettime（rt）
            self.cpp_info.system_libs = ["pthread", "rt"]
        # hidapi 传递依赖由 conan 自动传播（CMakeDeps 需要 requires 已声明）
