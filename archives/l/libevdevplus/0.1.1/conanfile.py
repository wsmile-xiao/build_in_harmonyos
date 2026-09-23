#!/usr/bin/env python3
"""Conan recipe — libevdevplus 0.1.1 (CMake).

libevdevplus 是 YukiWorkshop 出品的 C++ 事件设备（evdev）封装库：在 Linux
evdev 内核接口之上提供 EventDevice / EventDeviceID / InputEvent 等易用 C++ 类，
并附一套键盘码映射表（Table_ModifierKeys / Table_FunctionKeys / Table_LowerKeys /
Table_UpperKeys / Table_KeyCodes）。

构建系统：CMake（CMAKE_CXX_STANDARD 11）。上游 CMakeLists.txt **无条件**同时
构建两个目标并都安装：

    add_library(evdevPlus SHARED ${SOURCE_FILES})
    add_library(evdevPlus_Static STATIC ${SOURCE_FILES})   # OUTPUT_NAME evdevPlus
    install(TARGETS evdevPlus        LIBRARY DESTINATION ...)
    install(TARGETS evdevPlus_Static DESTINATION ...)

即上游不响应 Conan 惯用的 ``BUILD_SHARED_LIBS``（配方不设该变量，避免给出
"设了但无效"的假开关）；``options.shared`` 的落地方式是在 ``package()`` 里只保留
所选变体（shared=False 删 .so*，shared=True 删 .a），使同一包内不会 .so/.a 并存
导致下游链接歧义。默认静态，与仓库 CMake 模板一致。

与知识图谱的关系：E288 收录了同一族问题（"上游显式定义 STATIC 和 SHARED 两个目标
时 BUILD_SHARED_LIBS 不参与目标类型选择"），其推荐方案是打补丁把双目标改成单个
未指定类型的 ``add_library``（仓库内先例：``archives/l/libcork/0.9.0`` 的
``0003-src-CMakeLists-shared-libs.patch``）。本配方**选择零补丁的 packaging 级方案**，
理由：① R8 要求不偏离上游逻辑流，而上游是**刻意**同时交付 shared 与 static 两种产物；
② 目标状态（包内只留所选变体、选项真实生效）与 E288 推荐方案一致，且无任何机械门禁
依赖 ``BUILD_SHARED_LIBS``（已核 ``ci/conan/build_and_test.sh`` 与 ``preflight.py``）；
③ 避免为本包改动上游构建逻辑带来的回归面。若后续仓库要求统一到 E288 形态，替换成本
仅为一个小补丁 + ``tc.variables["BUILD_SHARED_LIBS"]``（已用最小夹具实测：单目标 +
仅 ``LIBRARY DESTINATION`` 在 static/shared 两种情形下 install 均正常）。

OHOS 适配：源码只依赖 C++ 标准库与 POSIX/Linux UAPI 头，其中
``<linux/uinput.h>`` 由 OHOS SDK sysroot 直接提供（实测
``.../ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include/linux/uinput.h``，
同目录另有 input.h / input-event-codes.h），因此**无补丁、无平台宏、无外部依赖**。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibevdevplusConan(ConanFile):
    name = "libevdevplus"
    version = "0.1.1"
    description = "Easy-to-use C++ event device (evdev) library"
    license = "MIT"
    homepage = "https://github.com/YukiWorkshop/libevdevPlus"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("evdev", "input", "uinput", "linux-uapi", "cpp11")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # 上游首行是 cmake_minimum_required(VERSION 3.0)；CMake 4.x（本机 4.1.2，
        # CI 同为 4.x）已移除对 <3.5 的兼容，configure 直接 hard error：
        #   "Compatibility with CMake < 3.5 has been removed from CMake."
        # 该检查发生在 CMakeLists.txt 第一行，早于 conan_toolchain.cmake 加载，
        # 因此 tc.variables/tc.cache_variables 都不可达（写进 toolchain 也不生效），
        # 必须用命令行缓存变量 CMAKE_POLICY_VERSION_MINIMUM（coordgen 先例）。
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._keep_requested_library_variant()

    def package_info(self):
        # 上游安装产物为 include/evdevPlus/*.hpp + lib/libevdevPlus.{a,so*} +
        # lib/pkgconfig/evdevPlus.pc（Name: evdevPlus）。上游不导出 CMake config，
        # 因此只对齐 pkg-config 名；CMake 侧走 Conan 默认（libevdevplus::libevdevplus）。
        self.cpp_info.libs = ["evdevPlus"]
        self.cpp_info.set_property("pkg_config_name", "evdevPlus")

    # ── Helper methods ──────────────────────────────────────────

    def _keep_requested_library_variant(self):
        """只保留 options.shared 选中的库变体（上游无条件同时安装两者）。

        上游 CMakeLists.txt 里 evdevPlus(SHARED) 与 evdevPlus_Static(STATIC) 是
        两个独立目标、OUTPUT_NAME 同为 evdevPlus，install() 会把 .so* 与 .a 一起
        装进 lib/。若原样留在同一 Conan 包里，cpp_info.libs=["evdevPlus"] 的下游
        会随机偏好 .so，静态消费方会误链到动态库；这里按选项删除未选中的那一个。
        """
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for entry in sorted(os.listdir(libdir)):
            is_static = entry.endswith(".a")
            is_shared = ".so" in entry
            if not (is_static or is_shared):
                continue  # pkgconfig/ 等目录与非库文件不动
            drop = is_static if self.options.shared else is_shared
            if drop:
                os.remove(os.path.join(libdir, entry))
