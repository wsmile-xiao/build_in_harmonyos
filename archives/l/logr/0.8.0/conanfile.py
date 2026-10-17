#!/usr/bin/env python3
"""Conan recipe — logr 0.8.0 (cmake)

上游 logr 0.8.0（https://github.com/ngrodzitski/logr），C++17 header-only
INTERFACE 库：logr_base 仅依赖 fmt；spdlog/glog/log4cplus/boostlog 四类
backend 均为可选 INTERFACE 组件（默认开启）。无编译产物（bindirs 为空），
无 CLI，因此不需要 commands.json（R38 仅 tool 类型需要）。

OHOS 适配点：
1) 依赖版本对齐 ohpcd registry 实际可用版本（上游 conanfile.py 声明的
   fmt/11.2.0、spdlog/1.15.3、boost/1.83.0、benchmark/1.9.4 在该制品仓
   不存在）：fmt/12.2.0（与 spdlog/1.17.0 的 requires 对齐）、
   spdlog/1.17.0、glog/0.7.1、log4cplus/2.1.2、boost/1.84.0、
   gtest/1.17.0、benchmark/1.9.5。
2) 移除上游 configure() 对 spdlog.no_exceptions / log4cplus.unicode 的
   赋值——ohpcd 的 spdlog/log4cplus 配方只暴露 shared/fPIC 两个 option，
   对不存在的 option 赋值在 Conan 2 会直接抛错（该调参属上游基准微调，
   非 OHOS 适应性必需，见 notes.md）。
3) os=OHOS 时显式设置 CMAKE_SYSTEM_NAME=OHOS、CMAKE_SYSTEM_PROCESSOR=
   aarch64（与 fmt 11.1.3 等归档同一陷阱：conan 默认映射为 HarmonyOS，
   cmake 无同名平台文件会静默丢平台变量）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import apply_conandata_patches, get, rmdir
from conan.tools.scm import Version

required_conan_version = ">=1.53.0"


class LogrConan(ConanFile):
    name = "logr"
    version = "0.8.0"
    license = "BSD 3-Clause License"
    author = "Nicolai Grodzitski <utromvecherom@gmail.com>"
    url = "https://github.com/ngrodzitski/logr"
    description = "Logger frontend substitution for spdlog, glog, etc for server/desktop applications"
    topics = ("logger", "development", "util", "utils")
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    options = { 'spdlog_backend' : [True, False],
                'glog_backend' : [True, False],
                'log4cplus_backend' : [True, False],
                'boostlog_backend' : [True, False] }

    default_options = { 'spdlog_backend': True,
                        'glog_backend': True,
                        'log4cplus_backend': True,
                        # OHOS 适配：ohpcd 的 boost/1.84.0 未提供 Boost::log
                        # 组件（CMakeDeps 只声明 headers/regex/program_options/
                        # system/date_time/filesystem/iostreams），启用该后端会在
                        # configure 阶段报 "Boost::log target was not found"，
                        # 因此默认关闭（option 保留，可用带 log 组件的 boost 开启）。
                        'boostlog_backend': False }

    no_copy_source = False
    build_policy = "missing"

    def _compiler_support_lut(self):
        return {
            "gcc": "9",
            "clang": "11",
            "apple-clang": "12",
            "Visual Studio": "17",
            "msvc": "191"
        }

    # This hint tells that this conanfile acts as
    # a conanfile for a package, which implies
    # it is responsible only for library itself.
    # Used to eliminate tests-related stuff (gtest, building tests)
    ACT_AS_PACKAGE_ONLY_CONANFILE = False

    def _is_package_only(self):
        return (
            self.ACT_AS_PACKAGE_ONLY_CONANFILE
            # The environment variable below can be used
            # to run conan create localy (used for debugging issues).
            or os.environ.get("LOGR_CONAN_PACKAGING") == "ON"
        )

    def requirements(self):
        self.requires("fmt/12.2.0")  # 与 spdlog/1.17.0 (ohpcd) 的 requires 对齐

        if self.options.spdlog_backend:
            self.requires("spdlog/1.17.0")

        if self.options.glog_backend:
            self.requires("glog/0.7.1")

        if self.options.log4cplus_backend:
            self.requires("log4cplus/2.1.2")

        if self.options.boostlog_backend:
            self.requires("boost/1.84.0")

    def build_requirements(self):
        if not self._is_package_only():
            # OHOS 适配：gtest/1.17.0 (ohpcd) 的 cmake_file_name=gtest 且只提供
            # gtest::gtest 单目标，上游测试链接的 GTest::gmock_main 不存在；
            # 1.17.0.1/1.17.0.2 (ohpcd) 用 cmake_file_name=GTest 并声明了
            # GTest::gmock_main 等组件，因此用 1.17.0.1（benchmark 配方同款）。
            self.test_requires("gtest/1.17.0.1")
            self.test_requires("benchmark/1.9.5")

    def configure(self):
        # OHOS 适配：ohpcd 的 spdlog/log4cplus 配方仅暴露 shared/fPIC，
        # 不设置上游的 no_exceptions/unicode 调参（见文件头注释 2）。
        pass

    def validate(self):
        minimal_cpp_standard = "17"
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, minimal_cpp_standard)
        minimal_version = self._compiler_support_lut()

        compiler = str(self.settings.compiler)
        if compiler not in minimal_version:
            self.output.warning(
                "%s recipe lacks information about the %s compiler standard version support" % (self.name, compiler))
            self.output.warning(
                "%s requires a compiler that supports at least C++%s" % (self.name, minimal_cpp_standard))
            return

        version = Version(self.settings.compiler.version)
        if version < minimal_version[compiler]:
            raise ConanInvalidConfiguration("%s requires a compiler that supports at least C++%s" % (self.name, minimal_cpp_standard))

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 上游 tag tarball 不含 git 子模块 cmake-scripts（.gitmodules 声明，
        # 固定提交 bf753c71fefe9b505874d077483db84e6b5c4231）。显式拉取该
        # 子模块 tarball 到 cmake-scripts/，否则 configure 报
        # "include could not find requested file: .../cmake-scripts/...".
        sub = self.conan_data["submodules"]["cmake-scripts"]
        get(self, url=sub["url"], sha256=sub["sha256"],
            strip_root=True, destination="cmake-scripts")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS 适配（文件头注释 3）：与 fmt 归档同因，必须显式指回 OHOS。
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.variables["LOGR_INSTALL"] = True
        tc.variables[
            "LOGR_BUILD_TESTS"
        ] = not self._is_package_only()
        tc.variables[
            "LOGR_BUILD_EXAMPLES"
        ] = not self._is_package_only()
        tc.variables[
            "LOGR_BUILD_BENCHMARK"
        ] = not self._is_package_only()

        tc.variables['LOGR_WITH_SPDLOG_BACKEND'] = self.options.spdlog_backend
        tc.variables['LOGR_WITH_GLOG_BACKEND'] = self.options.glog_backend
        tc.variables['LOGR_WITH_LOG4CPLUS_BACKEND'] = self.options.log4cplus_backend
        tc.variables['LOGR_WITH_BOOSTLOG_BACKEND'] = self.options.boostlog_backend

        tc.generate()

        cmake_deps = CMakeDeps(self)
        cmake_deps.generate()

    def package_id(self):
        self.info.clear()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        if not self._is_package_only():
            cmake.build()
            cmake.test()
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.frameworkdirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "logr")

        self.cpp_info.names["cmake_find_package"] = "logr"
        self.cpp_info.names["cmake_find_package_multi"] = "logr"

        self.cpp_info.components["logr_base"].includedirs = ["include"]
        self.cpp_info.components["logr_base"].requires = ["fmt::fmt"]

        if self.options.spdlog_backend:
            self.cpp_info.components["logr_spdlog"].includedirs = []
            self.cpp_info.components["logr_spdlog"].requires = [
                "logr_base",
                "spdlog::spdlog",
            ]
        if self.options.glog_backend:
            self.cpp_info.components["logr_glog"].includedirs = []
            self.cpp_info.components["logr_glog"].requires = [
                "logr_base",
                "glog::glog",
            ]
        if self.options.log4cplus_backend:
            self.cpp_info.components["logr_log4cplus"].includedirs = []
            self.cpp_info.components["logr_log4cplus"].requires = [
                "logr_base",
                "log4cplus::log4cplus",
            ]
        if self.options.boostlog_backend:
            self.cpp_info.components["logr_boostlog"].includedirs = []
            self.cpp_info.components["logr_boostlog"].requires = [
                "logr_base",
                "boost::log",
            ]