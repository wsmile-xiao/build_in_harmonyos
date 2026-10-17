#!/usr/bin/env python3
"""Conan recipe for coordgen (Schoedinger coordgenlibs) — 2D chemical
structure coordinate generation library."""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.errors import ConanInvalidConfiguration


class CoordgenConan(ConanFile):
    name = "coordgen"
    version = "3.0.2"
    description = ("2D coordinate generation for chemical structures "
                   "(Schoedinger sketcher minimizer, coordgenlibs)")
    license = "BSD-3-Clause"
    url = "https://github.com/schrodinger/coordgenlibs"
    homepage = "https://github.com/schrodinger/coordgenlibs"
    topics = ("chemistry", "coordinate-generation", "sketcher", "schrodinger")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    @property
    def _min_cppstd(self):
        return 11

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 上游默认 COORDGEN_USE_MAEPARSER=OFF：模板数据编译期内嵌
        # （CoordgenTemplates.cpp），库本体零依赖。上游测试所需的
        # maeparser/Boost 只在原生探索阶段使用，不进入包依赖链。
        pass

    def validate_build(self):
        # cppstd values like "gnu98" carry a prefix; strip non-digits.
        cppstd = str(self.settings.compiler.get_safe("cppstd") or "")
        digits = "".join(ch for ch in cppstd if ch.isdigit())
        if digits and int(digits) < self._min_cppstd:
            raise ConanInvalidConfiguration(
                f"{self.ref} requires C++{self._min_cppstd} or higher")

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 上游 CI 口径：COORDGEN_RIGOROUS_BUILD=ON（-Wall -Wextra -Werror），
        # 库本体在 OHOS clang 15 下零告警通过（原生探索实证）。
        tc.variables["COORDGEN_RIGOROUS_BUILD"] = True
        # 打包只构建库；上游测试/example 在原生探索阶段单独执行。
        tc.variables["COORDGEN_BUILD_TESTS"] = False
        tc.variables["COORDGEN_BUILD_EXAMPLE"] = False
        tc.variables["COORDGEN_BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # 上游 CMakeLists 首行 cmake_minimum_required(3.2)：该检查发生在
        # project() 加载 toolchain 之前，toolchain 内 set() 不生效，必须以
        # 命令行缓存变量传入（cmake_minimum_required 在 project() 之前执行；
        # 既有正式知识 E103）。设备/CI CMake 4.1.2 需要该变量。
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["coordgen"]
        # 与上游 install(EXPORT coordgen-targets) 的命名空间保持一致。
        self.cpp_info.set_property("cmake_file_name", "coordgen")
        self.cpp_info.set_property("cmake_target_name", "coordgen::coordgen")
