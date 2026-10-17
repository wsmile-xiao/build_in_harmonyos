#!/usr/bin/env python3
"""Conan recipe for Boost 1.90.0.4 Morpheus/pinocchio compiled components."""

import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    copy,
    export_conandata_patches,
    get,
)


class BoostConan(ConanFile):
    name = "boost"
    version = "1.90.0.4.2"
    description = "Boost C++ libraries with Morpheus/pinocchio-required compiled components"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = "https://github.com/boostorg/boost"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if str(self.settings.os) == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_TESTING"] = False
        # 1.90.0.1 的组件集不含 serialization / asio / graph，
        # pinocchio 4.1.0 要 `Boost COMPONENTS filesystem serialization`，
        # 且其 serialization/serializable.hpp 直接 #include <boost/asio/streambuf.hpp>，
        # 实测报 "fatal error: 'boost/asio/streambuf.hpp' file not found"。
        # 本版（1.90.0.2）在原集合上**只增不减**，老版本原样保留不受影响。
        tc.variables["BOOST_INCLUDE_LIBRARIES"] = (
            # 组件集 = 原 1.90.0.1 的集合（只增不减）+ pinocchio 4.1.0 实际需要的。
            #
            # ⚠️ **`#include <boost/X>` 里的 X 不等于 boost 的库名**，不能直接拿来当组件：
            #     boost/next_prior.hpp → utility        boost/shared_ptr.hpp → smart_ptr
            #     boost/version.hpp    → config         boost/none.hpp       → optional
            #     boost/archive/*      → serialization  boost/blank.hpp      → utility
            # 上一轮把 include 目录名直接当库名，漏了 utility，撞 next_prior.hpp not found。
            #
            # 头文件库加进来成本近乎为零（只多装头、不增编译时间），故宁可给足。
            "algorithm;array;asio;assert;atomic;bind;circular_buffer;concept_check;"
            "config;container;container_hash;conversion;core;detail;dynamic_bitset;"
            "filesystem;foreach;function;functional;fusion;graph;integer;io;iostreams;"
            "iterator;lexical_cast;logic;math;move;mpl;multiprecision;numeric/conversion;"
            "optional;predef;preprocessor;program_options;property_tree;range;ratio;"
            "serialization;smart_ptr;static_assert;system;throw_exception;tokenizer;"
            "tuple;type_index;type_traits;typeof;utility;variant;winapi;"
            # ── 1.90.0.3 新增：ecell4-base 2.1.2 需要 ──────────────────────
            # ⚠️ 嵌套库要用**斜杠**：numeric/interval，不是 numeric_interval。
            # 依据 tools/cmake/include/BoostRoot.cmake:308 —
            #   file(GLOB __boost_libraries RELATIVE .../libs "libs/*/CMakeLists.txt"
            #                                                 "libs/numeric/*/CMakeLists.txt")
            # 校验是 "${lib}/CMakeLists.txt" IN_LIST __boost_libraries，
            # 列表项形如 numeric/interval/CMakeLists.txt。
            # （第 258 行那个 ^numeric_ → numeric/ 的替换只作用于**依赖名**，不是这里。）
            # 写错不会报错、只 WARNING「has not been found」，然后**静默不装那些头**——
            # 实证：1.90.0.2 起 numeric_conversion 就是错的，一直没人发现，
            # 因为它被别的库当依赖捎带进来了；而 interval/odeint/ublas 没人捎带，头就真缺了。
            # 前三个 + interval/odeint/ublas 都是 header-only（INTERFACE 库），
            # 加进来零编译开销；**regex 是编译型**，是本次唯一有实际构建成本的。
            "format;multi_array;ptr_container;regex;"
            "numeric/interval;numeric/odeint;numeric/ublas;"
            # ── 1.90.0.4 新增：pinocchio 4.1.0 unittest 需要 ──────────────────────────
            # pinocchio 4.1.0 上游测试链 find_package(Boost COMPONENTS unit_test_framework)
            # + BOOST_TEST_DYN_LINK，需要 libboost_unit_test_framework.so + boost/test/ 头。
            # test 是编译型组件：libs/test 构建 prg_exec_monitor、
            # test_exec_monitor（静态）、unit_test_framework（共享）。
            # 其 _boost_test_dependencies 依赖 algorithm/assert/bind/config/core/detail/
            # describe/exception/function/io/iterator/mpl/numeric_conversion/optional/
            # preprocessor/smart_ptr/static_assert/type_traits/utility（全部 header-only）。
            # 除 describe/exception 外已在上面列出；余下的 BoostRoot.cmake
            # 的 __boost_gather_dependencies 会自动捧带并安装缺的头字段库。
            "test;describe;exception"
        )
        tc.variables["BOOST_EXCLUDE_LIBRARIES"] = "context;coroutine;fiber"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_ICU"] = True
        tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"

        if str(self.settings.os) == "OHOS":
            tc.variables["BOOST_INSTALL_NO_VERSIONED_LIBS"] = True
            tc.variables["BOOST_FILESYSTEM_DISABLE_STATX"] = True
            tc.variables["BOOST_FILESYSTEM_DISABLE_COPY_FILE_RANGE"] = True
            for language in ("C", "CXX"):
                tc.variables[
                    f"CMAKE_SHARED_LIBRARY_SONAME_{language}_FLAG"
                ] = "-Wl,-soname,"
                tc.variables[
                    f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG"
                ] = "-Wl,-rpath,"
                tc.variables[
                    f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG_SEP"
                ] = ":"
                tc.variables[
                    f"CMAKE_SHARED_LIBRARY_RPATH_LINK_{language}_FLAG"
                ] = "-Wl,-rpath-link,"
            tc.variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE_1_0.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        if str(self.settings.os) != "OHOS" or not self.options.shared:
            return

        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            self.output.warning(
                "OHOS signing tools are unavailable; native validation must sign shared libraries."
            )
            return

        libraries = glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True
        )
        for library in libraries:
            if os.path.islink(library):
                continue
            self._sign_elf_atomically(library, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(f'"{objcopy}" --remove-section .codesign "{temporary}"')
            self.run(
                f'"{signer}" sign -inFile "{temporary}" '
                f'-outFile "{temporary}" -selfSign 1'
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((path for path in candidates if os.path.isfile(path)), "")

    def _component_library(self, available_libraries, component):
        exact = f"boost_{component}"
        if exact in available_libraries:
            return exact
        matches = sorted(
            library
            for library in available_libraries
            if library.startswith(f"boost_{component}")
        )
        if not matches:
            self.output.warning(
                f"Component '{component}': no library matching 'boost_{component}' found"
            )
        return matches[0] if matches else ""

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Boost")
        self.cpp_info.includedirs = ["include"]
        available_libraries = set(collect_libs(self))

        for name in ("headers",):
            component = self.cpp_info.components[name]
            component.includedirs = ["include"]
            component.set_property("cmake_target_name", f"Boost::{name}")

        for name in (
            "atomic",
            "container",
            "filesystem",
            "program_options",
            "system",
            "unit_test_framework",
        ):
            component = self.cpp_info.components[name]
            component.includedirs = ["include"]
            library = self._component_library(available_libraries, name)
            if library:
                component.libs = [library]
            component.set_property("cmake_target_name", f"Boost::{name}")

        self.cpp_info.components["filesystem"].requires = ["atomic", "system"]
        self.cpp_info.components["program_options"].requires = [
            "container",
            "headers",
        ]
        # unit_test_framework: 纯 header 依赖（algorithm/core/config/... 全部 header-only），
        # 无其他编译型 boost 依赖，只需 headers 组件的 include 路径。
        self.cpp_info.components["unit_test_framework"].requires = ["headers"]
        # 对齐上游 boost-cmake：共享版 unit_test_framework 目标会 PUBLIC 传播
        # BOOST_TEST_DYN_LINK（见 libs/test/CMakeLists.txt）。pinocchio 4.1.0 也
        # 自己定义同值 BOOST_TEST_DYN_LINK，无冲突；此处显式传播减少消费者摩擦。
        if self.options.shared:
            self.cpp_info.components["unit_test_framework"].defines = [
                "BOOST_TEST_DYN_LINK"
            ]
