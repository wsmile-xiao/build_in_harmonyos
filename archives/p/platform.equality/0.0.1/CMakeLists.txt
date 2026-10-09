cmake_minimum_required(VERSION 3.17)
project(platform.equality.tests CXX)

# 只用上游真实的测试源文件（Platform.Equality.Tests.cpp，5 个 TEST 用例）。
# 不引入上游 cpp/CMakeLists.txt 与 Platform.Equality.Tests/CMakeLists.txt：
# 后者在 configure 期用 FetchContent 从 GitHub 拉 googletest，OHOS CI 不可达；
# 这里改用 Conan 制品仓里的 gtest（见 conanfile.py requirements()）。
set(PEEQ_CXX_STANDARD 20 CACHE STRING "C++ standard for the upstream tests")
set(CMAKE_CXX_STANDARD ${PEEQ_CXX_STANDARD})
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

enable_testing()

# 注意：这里用 find_package(gtest)，target 为 gtest::gtest —— 与 Conan 的
# CMakeDeps 生成的 gtest-config.cmake 一致（CMakeDeps 按包名小写生成 config，
# 暴露 <包名>::<组件>）。若写成 find_package(GTest)+GTest::gtest，CMake 会
# 回退到内置 FindGTest.cmake 去找系统 gtest，使 test_requires("gtest/1.17.0")
# 的 pin 失效（本地检视第 3 轮 P2-1）。
find_package(gtest REQUIRED CONFIG)

# 被测库本体：上游 cpp/Platform.Equality 是 INTERFACE 库（header-only）。
add_library(Platform.Equality.Library INTERFACE)
target_include_directories(Platform.Equality.Library INTERFACE
    "${CMAKE_CURRENT_SOURCE_DIR}/cpp/Platform.Equality")

add_executable(Platform.Equality.Tests
    "${CMAKE_CURRENT_SOURCE_DIR}/cpp/Platform.Equality.Tests/Platform.Equality.Tests.cpp")
# Conan 的 gtest 配方只暴露 gtest::gtest（= libgtest.a），没有 gtest_main 的
# component（libgtest_main.a 实际有随包发布）。上游测试源文件**没有 main()**，
# 因此需另行链接 gtest_main。这里从 CMakeDeps 已解析出的同一包目录里定位它，
# 保证用的是 Conan pin 的 gtest/1.17.0，而不是系统 gtest。
# CMakeDeps 为每个包导出 <pkg>_PACKAGE_FOLDER_<CONFIG>（纯路径，无生成器表达式），
# 直接用它定位同包的 gtest_main，避免去解析带 $<CONFIG:...> 的 INTERFACE 属性。
# CMakeDeps 为每个包导出 <pkg>_PACKAGE_FOLDER_<CONFIG>。配置后缀随
# CMAKE_BUILD_TYPE 变化（RELEASE/DEBUG/RELWITHDEBINFO...），因此按当前
# build type 拼后缀，而不是硬编码 RELEASE —— 否则 -s build_type=Debug
# 会在 configure 期直接中止，且报错原因与被测逻辑无关。
string(TOUPPER "${CMAKE_BUILD_TYPE}" _peq_cfg)
if(NOT _peq_cfg)
    set(_peq_cfg "RELEASE")
endif()
set(gtest_PACKAGE_FOLDER_VAR "gtest_PACKAGE_FOLDER_${_peq_cfg}")
if(NOT DEFINED ${gtest_PACKAGE_FOLDER_VAR})
    message(FATAL_ERROR
        "${gtest_PACKAGE_FOLDER_VAR} is not defined -- CMakeDeps did not "
        "resolve the Conan gtest package for build type '${CMAKE_BUILD_TYPE}'; "
        "refusing to fall back to system gtest.")
endif()
set(_gtest_pkg "${${gtest_PACKAGE_FOLDER_VAR}}")

# 上游测试源文件没有 main()，需额外链接 libgtest_main.a。Conan 的 gtest 配方
# 只暴露 gtest::gtest 组件，故从同一已解析包目录里定位 gtest_main。
# 取第一个命中的候选（lib 优先于 lib64）后立即 break，避免"最后一个匹配项
# 静默生效"——后续增删候选会悄悄改变链接对象。
set(_gtest_main_lib "")
foreach(_cand
        "${_gtest_pkg}/lib/libgtest_main.a"
        "${_gtest_pkg}/lib64/libgtest_main.a")
    if(EXISTS "${_cand}")
        set(_gtest_main_lib "${_cand}")
        break()
    endif()
endforeach()
if(NOT _gtest_main_lib)
    message(FATAL_ERROR
        "libgtest_main.a not found under ${_gtest_pkg} -- the Conan gtest "
        "package layout changed; refusing to fall back to system gtest.")
endif()
message(STATUS "Using gtest_main: ${_gtest_main_lib}")

target_link_libraries(Platform.Equality.Tests PRIVATE
    Platform.Equality.Library gtest::gtest "${_gtest_main_lib}")

# 注意：不能用 gtest_discover_tests()——它在构建期执行测试二进制来枚举用例，
# 交叉编译下二进制是 aarch64，构建机跑不了。改用 add_test +
# CTest 的 CROSSCOMPILING_EMULATOR（ohos-aarch64-run profile 里已配 qemu）。
add_test(NAME Platform.Equality.Tests COMMAND Platform.Equality.Tests)
