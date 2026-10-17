cmake_minimum_required(VERSION 3.15)
project(permlib_upstream_tests LANGUAGES CXX)

# ── permlib 0.2.9 上游测试驱动（配方自带，不改上游源码的构建描述）───────────────
# 为什么不用上游自带的 CMakeLists：上游 test/CMakeLists.txt 用 legacy 变量
# ${Boost_UNIT_TEST_FRAMEWORK_LIBRARY} 链接 Boost.Test，而 Conan 生成的
# BoostConfig.cmake（CMakeDeps）只提供 imported target，不提供该 legacy 变量 ——
# 链接行会退化成空，或者 find_package 命中设备里其它 Boost 配置（假绿）。
# 本文件构建的是**同一批上游源文件**（test/*.cpp，一字未改），并注册到 ctest。
#
# 变量由配方用 CMakeToolchain(tc.variables) 注入（cache_variables 不进
# conan_toolchain.cmake，project() 之前读会静默退化）。

if(NOT DEFINED PERMLIB_SOURCE_DIR OR NOT IS_DIRECTORY "${PERMLIB_SOURCE_DIR}")
    message(FATAL_ERROR "PERMLIB_SOURCE_DIR 未注入或不是目录: '${PERMLIB_SOURCE_DIR}'")
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 上游语料用相对路径 "../data/G_*" 读取 ⇒ 用例的运行目录必须是 <root>/test，
# 且 <root>/data 存在（上游 CMakeLists 也是把 data/ 拷到构建根目录）。
set(PERMLIB_TEST_ROOT "${CMAKE_BINARY_DIR}")
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${PERMLIB_TEST_ROOT}/test")
file(COPY "${PERMLIB_SOURCE_DIR}/data" DESTINATION "${PERMLIB_TEST_ROOT}")

# CMakeDeps 生成的 BoostConfig.cmake（组件 Boost::headers / Boost::unit_test_framework）。
# 用 CONFIG 模式避免 Module 模式去找系统 Boost。
find_package(Boost CONFIG REQUIRED)

if(NOT Boost_INCLUDE_DIRS)
    message(FATAL_ERROR "Boost_INCLUDE_DIRS 为空 —— Boost 头文件路径未传递，拒绝静默降级")
endif()

set(PERMLIB_UPSTREAM_TESTS
    test-base
    test-trans
    test-generators
    test-partition
    test-permutation
    test-search-setstabilizer
    test-symmetric-group
    test-search-matrixauto
    test-orbit-lex-min
    test-api
    test-test
    test-export
    test-abstract-groups
)

enable_testing()

foreach(_test IN LISTS PERMLIB_UPSTREAM_TESTS)
    if(NOT EXISTS "${PERMLIB_SOURCE_DIR}/test/${_test}.cpp")
        message(FATAL_ERROR "缺少上游用例源文件 test/${_test}.cpp")
    endif()
    add_executable(${_test} "${PERMLIB_SOURCE_DIR}/test/${_test}.cpp")
    target_include_directories(${_test} PRIVATE "${PERMLIB_SOURCE_DIR}/include")
    target_link_libraries(${_test} PRIVATE Boost::unit_test_framework)
    add_test(NAME ${_test} COMMAND ${_test} --report_level=detailed)
    set_tests_properties(${_test} PROPERTIES WORKING_DIRECTORY "${PERMLIB_TEST_ROOT}/test")
endforeach()
