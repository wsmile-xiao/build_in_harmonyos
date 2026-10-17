#!/usr/bin/env python3
"""Conan recipe — fusion 1.3.3 (cmake)

上游 xioTechnologies/Fusion 1.3.3：IMU 传感器融合库（AHRS 姿态解算 +
Bias/Compass 校准 + Remap 坐标重映射 + Inertial/Magnetic 传感器模型），
C 实现，无第三方运行时依赖。上游 CMake 只产出静态库 libFusion.a 与
C 示例（Simple/Advanced），未提供 install 规则，故 package() 手动装配
头文件与静态库。

产物：include/Fusion/{全部公开头} + lib/libFusion.a。无 CLI（library package，
示例程序不装包，R38 不适用）。
"""
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os

required_conan_version = ">=2.0"


class FusionConan(ConanFile):
    name = "fusion"
    version = "1.3.3"
    package_type = "library"

    description = (
        "IMU sensor fusion library in C: AHRS (attitude and heading "
        "reference system), bias estimation, magnetometer compensation, "
        "coordinate remapping and inertial/magnetic sensor models."
    )
    homepage = "https://github.com/xioTechnologies/Fusion"
    license = "MIT"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("imu", "sensor-fusion", "ahrs", "madgwick", "mahony", "c")

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="")
        # 上游无 install 规则，目标固定为 Fusion（libFusion.a）
        cmake.build(target=["Fusion"])

    def package(self):
        # 上游 CMake 无 install 规则：手动装配公开头 + 库。
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "Fusion"),
             dst=os.path.join(self.package_folder, "include", "Fusion"))
        if self.options.shared:
            # BUILD_SHARED_LIBS=ON 时上游产 libFusion.so
            libname = "libFusion.so"
            copy(self, libname,
                 src=os.path.join(self.build_folder, "Fusion"),
                 dst=os.path.join(self.package_folder, "lib"))
        else:
            libname = "libFusion.a"
            copy(self, libname,
                 src=os.path.join(self.build_folder, "Fusion"),
                 dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE.md",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["Fusion"]
        # 上游在 UNIX 平台链接数学库（R32：os 判断须用 in ("Linux", "OHOS")）
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "fusion")
        self.cpp_info.set_property("cmake_target_name", "fusion::fusion")