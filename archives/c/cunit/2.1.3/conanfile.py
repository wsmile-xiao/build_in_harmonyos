from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    save, copy, get, rmdir, load
)
from conan.tools.layout import basic_layout
from conan.tools.cmake import CMake, CMakeToolchain
import os

required_conan_version = ">=2.0"

CMAKELISTS_CONTENT = r"""
cmake_minimum_required(VERSION 3.15)
project(cunit VERSION 2.1.3 LANGUAGES C)
include(GNUInstallDirs)

option(ENABLE_BASIC     "Enable Basic interface"     ON)
option(ENABLE_CONSOLE   "Enable Console interface"   ON)
option(ENABLE_AUTOMATED "Enable Automated interface" ON)
# 上游 autotools `make check` 路径：ENABLE_TEST 触发 libcunit_test.a + test_cunit exec
# 复刻上游 CUnit/Sources/Makefile.am + Test/Makefile.am 的测试构建逻辑
option(ENABLE_TEST      "Enable upstream self-tests" ON)

set(CUNIT_SOURCES
    CUnit/Sources/Framework/CUError.c
    CUnit/Sources/Framework/MyMem.c
    CUnit/Sources/Framework/TestDB.c
    CUnit/Sources/Framework/TestRun.c
    CUnit/Sources/Framework/Util.c
)

set(CUNIT_HEADERS
    CUnit/Headers/CUError.h
    CUnit/Headers/MyMem.h
    CUnit/Headers/TestDB.h
    CUnit/Headers/TestRun.h
    CUnit/Headers/Util.h
    CUnit/Headers/CUnit.h
    CUnit/Headers/CUnit_intl.h
)

if(ENABLE_BASIC)
    list(APPEND CUNIT_SOURCES CUnit/Sources/Basic/Basic.c)
    list(APPEND CUNIT_HEADERS CUnit/Headers/Basic.h)
endif()

if(ENABLE_CONSOLE)
    list(APPEND CUNIT_SOURCES CUnit/Sources/Console/Console.c)
    list(APPEND CUNIT_HEADERS CUnit/Headers/Console.h)
endif()

if(ENABLE_AUTOMATED)
    list(APPEND CUNIT_SOURCES CUnit/Sources/Automated/Automated.c)
    list(APPEND CUNIT_HEADERS CUnit/Headers/Automated.h)
endif()

add_library(cunit ${CUNIT_SOURCES})
add_library(CUnit::cunit ALIAS cunit)

target_include_directories(cunit
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/CUnit/Headers>
        $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
)

set_target_properties(cunit PROPERTIES
    C_STANDARD 99
    C_STANDARD_REQUIRED ON
    POSITION_INDEPENDENT_CODE ON
    OUTPUT_NAME cunit
)

include(CheckLibraryExists)
check_library_exists(m floor "" HAVE_LIBM)
if(HAVE_LIBM)
    target_link_libraries(cunit PRIVATE m)
endif()

install(TARGETS cunit
    EXPORT cunit-targets
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
)

install(FILES ${CUNIT_HEADERS}
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/CUnit
)

install(EXPORT cunit-targets
    FILE cunit-targets.cmake
    NAMESPACE CUnit::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/cunit
)

include(CMakePackageConfigHelpers)
configure_package_config_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/cunit-config.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/cunit-config.cmake
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/cunit
)

install(FILES
    ${CMAKE_CURRENT_BINARY_DIR}/cunit-config.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/cunit
)

# ── 上游自测路径（复刻 autotools ENABLE_TEST + make check）──────────────
# 上游 CUnit/Sources/Makefile.am：ENABLE_TEST 时编 libcunit_test.a
# （Framework 5 源 + -DMEMTRACE -DCUNIT_BUILD_TESTS -DCUNIT_DO_NOT_DEFINE_UNLESS_BUILDING_TESTS）
# 上游 Test/Makefile.am：test_cunit exec 链 libcunit_test.a，跑 5 个 test_cunit_<Module>()
if(ENABLE_TEST)
    # 上游 Framework 源在 CUNIT_BUILD_TESTS 守卫下额外暴露 test_cunit_<Module>() 函数
    add_library(cunit_test STATIC
        CUnit/Sources/Framework/CUError.c
        CUnit/Sources/Framework/MyMem.c
        CUnit/Sources/Framework/TestDB.c
        CUnit/Sources/Framework/TestRun.c
        CUnit/Sources/Framework/Util.c
    )
    target_include_directories(cunit_test PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/CUnit/Headers
        ${CMAKE_CURRENT_SOURCE_DIR}/CUnit/Sources/Test
    )
    target_compile_definitions(cunit_test PRIVATE
        MEMTRACE
        CUNIT_BUILD_TESTS
        CUNIT_DO_NOT_DEFINE_UNLESS_BUILDING_TESTS
        HAVE_STDARG_H
        HAVE_STRING_H
        ENABLE_BASIC
        ENABLE_CONSOLE
        ENABLE_AUTOMATED
    )
    set_target_properties(cunit_test PROPERTIES
        C_STANDARD 99
        POSITION_INDEPENDENT_CODE ON
        OUTPUT_NAME cunit_test
    )
    # test_cunit.c 聚合驱动：调 5 个 test_cunit_<Module>() + 内部 TEST() 断言宏
    add_executable(test_cunit CUnit/Sources/Test/test_cunit.c)
    target_include_directories(test_cunit PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/CUnit/Headers
        ${CMAKE_CURRENT_SOURCE_DIR}/CUnit/Sources/Test
    )
    target_compile_definitions(test_cunit PRIVATE
        MEMTRACE
        CUNIT_BUILD_TESTS
        CUNIT_DO_NOT_DEFINE_UNLESS_BUILDING_TESTS
        HAVE_STDARG_H
        HAVE_STRING_H
        ENABLE_BASIC
        ENABLE_CONSOLE
        ENABLE_AUTOMATED
    )
    # gate libm：Windows/MSVC 无独立 libm（数学函数在 ucrt），按上游 cunit lib 的 CheckLibraryExists 模式条件链接
    check_library_exists(m floor "" HAVE_LIBM_TEST)
    if(HAVE_LIBM_TEST)
        target_link_libraries(test_cunit PRIVATE cunit_test m)
    else()
        target_link_libraries(test_cunit PRIVATE cunit_test)
    endif()

    enable_testing()
    add_test(NAME test_cunit COMMAND test_cunit)
endif()
"""

CMAKE_CONFIG_IN = r"""@PACKAGE_INIT@
include("${CMAKE_CURRENT_LIST_DIR}/cunit-targets.cmake")
"""

class CunitConan(ConanFile):
    name = "cunit"
    version = "2.1.3"
    description = "CUnit - A Unit Testing Framework for C"
    license = "LGPL-2.1-or-later"
    url = "https://sourceforge.net/projects/cunit/"
    topics = ("unit-testing", "c", "testing", "tdd")
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

    def validate(self):
        if self.settings.os not in ["Linux", "OHOS", "Windows"]:
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux/OHOS/Windows, got {self.settings.os}")

    def config_options(self):
        # fPIC deletion handled in configure() to avoid double deletion under Conan 2.x
        pass

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        elif self.settings.os == "Windows":
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True, destination=self.source_folder)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

    def build(self):
        self._write_cmakelists()
        self._generate_cunit_header()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 跑上游 ctest 套件（ENABLE_TEST=ON）：test_cunit 驱动 5 个 test_cunit_<Module>()
        # 仅 native build 跑（can_run）：交叉编译 OHOS 时 target 二进制在 x86 host 无法执行，ctest 会中断
        from conan.tools.build import can_run
        if can_run(self):
            cmake.test()

    def _write_cmakelists(self):
        save(self, os.path.join(self.source_folder, "CMakeLists.txt"),
             CMAKELISTS_CONTENT.strip())
        save(self, os.path.join(self.source_folder, "cunit-config.cmake.in"),
             CMAKE_CONFIG_IN.strip())

    def _generate_cunit_header(self):
        header_in = os.path.join(self.source_folder, "CUnit", "Headers", "CUnit.h.in")
        header_out = os.path.join(self.source_folder, "CUnit", "Headers", "CUnit.h")
        if os.path.exists(header_in):
            content = load(self, header_in)
            replacements = {
                "@HAVE_STRING_H@": "1",
                "@HAVE_STDARG_H@": "1",
                "@HAVE_STDIO_H@": "1",
                "@HAVE_STDLIB_H@": "1",
                "@HAVE_TIME_H@": "1",
                "@HAVE_MATH_H@": "1",
                "@HAVE_FLOAT_H@": "1",
                "@HAVE_SYS_TIME_H@": "1",
                "@HAVE_MEMORY_H@": "1",
                "@HAVE_UNISTD_H@": "1",
                "@HAVE_DECL_H_ERRNO@": "1",
                "@HAVE_DECL_STRERROR@": "1",
                "@HAVE_SETJMP_H@": "1",
                "@CUNIT_BSD_DEPRECATED@": "",
                "@CUNIT_SUC_DEPRECATED@": "",
                "@CUNIT_DOXYGEN@": "0",
                "@ENABLE_BASIC@": "1",
                "@ENABLE_CONSOLE@": "1",
                "@ENABLE_AUTOMATED@": "1",
                "@ENABLE_CURSES@": "0",
                "@HAVE_LIBREADLINE@": "0",
                "@CUNIT_VERSION@": '"2.1.3"',
                "@CUNIT_MAJOR_VERSION@": "2",
                "@CUNIT_MINOR_VERSION@": "1",
                "@CUNIT_PATCH_VERSION@": "3",
            }
            for key, value in replacements.items():
                content = content.replace(key, value)
            save(self, header_out, content)
        else:
            self.output.info("CUnit.h.in not found; this should not happen with official source")
            # Fallback: generate a minimal CUnit.h for basic compilation
            save(self, header_out, '''/*
 * CUnit - A Unit Testing Framework for C (fallback header)
 */
#ifndef CUNIT_H
#define CUNIT_H
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <setjmp.h>
#ifdef __cplusplus
extern "C" {
#endif
#define CUNIT_VERSION "2.1.3"
#define CU_BASIC
#define CU_CONSOLE
#define CU_AUTOMATED
typedef enum { CUE_SUCCESS = 0, CUE_NOMEMORY = 1, CUE_NOREGISTRY = 2,
    CUE_REGISTRY_EXISTS = 3, CUE_NOSUITE = 4, CUE_NO_SUITENAME = 5,
    CUE_SINIT_FAILED = 6, CUE_SCLEAN_FAILED = 7, CUE_DUP_SUITE = 8,
    CUE_NOTEST = 9, CUE_NOSUCHTEST = 10, CUE_FAIL = 100, CUE_MAX = 200
} CU_ErrorCode;
typedef CU_ErrorCode (*CU_SetUpFunc)(void);
typedef CU_ErrorCode (*CU_TearDownFunc)(void);
typedef void (*CU_TestFunc)(void);
typedef struct CU_Suite CU_Suite;
typedef struct CU_Test CU_Test;
CU_ErrorCode CU_initialize_registry(void);
void CU_cleanup_registry(void);
CU_Suite *CU_add_suite(const char *strName, CU_SetUpFunc pSetUp, CU_TearDownFunc pTearDown);
CU_Test *CU_add_test(CU_Suite *pSuite, const char *strName, CU_TestFunc pTestFunc);
unsigned int CU_get_number_of_failures(void);
CU_ErrorCode CU_get_error(void);
#ifdef __cplusplus
}
#endif
#endif /* CUNIT_H */
''')

        # Ensure CUnit_intl.h exists
        intl_header = os.path.join(self.source_folder, "CUnit", "Headers", "CUnit_intl.h")
        if not os.path.exists(intl_header):
            self.output.info("CUnit_intl.h not found, generating default")
            save(self, intl_header, '''/*
 * CUnit_intl.h - Internationalization support
 * Auto-generated by Conan recipe
 */
#ifndef CUNIT_INTL_H
#define CUNIT_INTL_H

#ifdef __cplusplus
extern "C" {
#endif

#ifdef HAVE_STDARG_H
#include <stdarg.h>
#endif

#ifdef HAVE_STRING_H
#include <string.h>
#endif

#define _(String) String

#ifdef __cplusplus
}
#endif

#endif /* CUNIT_INTL_H */
''')

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), ignore_case=True)
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["cunit"]
        self.cpp_info.defines = ["HAVE_CUNIT"]
