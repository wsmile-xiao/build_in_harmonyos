cmake_minimum_required(VERSION 3.15)
# ICU 静态库是 C++ 实现（即使 API 是 C）。链接必须由 clang++ 驱动才能带上
# libc++/libc++abi 运行时，否则报 undefined symbol: __cxa_guard_abort /
# operator delete 等（CI 实测 b54819/b55279 复现）。
# 关键：CMake 的链接驱动语言取决于目标源文件的语言，project() 声明 CXX
# 并不改变纯 .c 目标的链接驱动（本地实测）。因此测试源必须是 .cpp。
project(test_icu C CXX)

# Find the package via Conan-generated CMakeDeps (global target: icu::icu)
find_package(icu REQUIRED)

add_executable(test_icu test.cpp)

# icu is built --enable-static with circular inter-library references
# (icuuc <-> icui18n), so a plain target_link_libraries(icu::icu) would drop
# members on the first pass. Wrap the three archives in a link group with the
# static dependency order icui18n -> icuuc -> icudata.
if(TARGET icu::icui18n AND TARGET icu::icuuc AND TARGET icu::icudata)
    target_link_libraries(test_icu PRIVATE
        $<LINK_GROUP:RESCAN,icu::icui18n icu::icuuc icu::icudata>)
else()
    target_link_libraries(test_icu PRIVATE icu::icu)
endif()

enable_testing()
add_test(NAME test_icu COMMAND test_icu)
