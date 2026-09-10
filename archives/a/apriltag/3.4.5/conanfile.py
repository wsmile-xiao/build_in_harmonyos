#!/usr/bin/env python3
"""Conan recipe for apriltag 3.4.5 (AprilTag 3, AprilRobotics).

AprilTag 是一个视觉基准系统（fiducial marker）检测库：给定灰度图像与 tag
family（tag36h11/tag25h9/...），输出检测到的 tag id 与角点。纯 C99、CMake
构建，仅依赖系统 threads 与 libm，零第三方库依赖（W0 预检通过）。检测器自带
四线检测/编解码/位姿估计，含 common/ 内部数学库（matd/svd/homography/unionfind）。

OHOS 适配要点：
- CMakeToolchain generic_system 显式映射（cmake_system_name=OHOS）绕过 CMake
  对未知平台的行为（与本仓 gcem/platform_folders 一致）。
- 上游把 -Werror 当"静态库代码卫生"用（CMake>=3.24 走
  CMAKE_COMPILE_WARNING_AS_ERROR ON，<3.24 走 add_compile_options(-Werror)）。
  该 set() 无 CACHE 关键字，无法用 -D 覆盖，只能打补丁（0001）摘掉。
- BUILD_TESTING=ON 时 test/ 注册 3 个 ctest（test_detection 对 3 张真实照片
  跑 tag36h11 全流程，与 test/data/*.txt 真值逐角点比对，容差 0.1px），
  build() 内 cmake.test() 直接实跑。
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
import os


class ApriltagConan(ConanFile):
    name = "apriltag"
    version = "3.4.5"
    description = "AprilTag is a visual fiducial system popular for robotics research"
    license = "BSD-2-Clause"
    homepage = "https://github.com/AprilRobotics/apriltag"
    url = ""  # CI fills this
    topics = ("fiducial", "april-tag", "vision", "tag-detection", "marker")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R32: OHOS/Linux 走 generic_system 显式映射（与本仓 gcem/platform_folders 一致）
        if self.settings.os in ("Linux", "OHOS"):
            tc.blocks["generic_system"].values["cmake_system_name"] = str(self.settings.os)
            if self.settings.os == "OHOS":
                tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        # 默认静态库（与上游 BUILD_SHARED_LIBS=ON 相反，本仓惯例静态默认）
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 关闭 python 绑定与 example 程序，只产库 + 头 + 测试
        tc.variables["BUILD_PYTHON_WRAPPER"] = "OFF"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        # 层1 上游官方测试：test/CMakeLists.txt 在 BUILD_TESTING=ON 时注册 3 个 ctest
        tc.variables["BUILD_TESTING"] = "ON"
        if not self.options.shared:
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON" if self.options.fPIC else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 层1 上游官方测试：3 个 test_detection ctest（照片真值逐角点比对）
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 安装的是库+头+pc+cmake 包配置；无 python 产物/无 share
        self._drop_rpath_artifacts()

    def _drop_rpath_artifacts(self):
        # 静态/共享库由 Conan 管理；清理可能带出的无用 pkgconfig/cmake 由
        # cmake_file/pkg_config_name 在 package_info 重新暴露，无需手动删。
        pass

    def package_info(self):
        # 上游头安装布局：include/apriltag/{apriltag.h,common/*.h,tag*.h}，
        # apriltag.h 以相对 include 引用 common/*.h，消费者 -I<prefix>/include/apriltag
        self.cpp_info.includedirs = ["include/apriltag"]
        self.cpp_info.libs = ["apriltag"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.set_property("cmake_file_name", "apriltag")
        self.cpp_info.set_property("cmake_target_name", "apriltag::apriltag")
        self.cpp_info.set_property("pkg_config_name", "apriltag")
