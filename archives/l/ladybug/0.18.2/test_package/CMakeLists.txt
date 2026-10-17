cmake_minimum_required(VERSION 3.15)
# liblbug.a 是 C++ 静态库（liblbug 内部大量使用 libc++ 符号：operator new、
# __cxa_*、std::mutex 等）。测试程序 test.c 虽为 C 源文件，但必须用 C++
# 链接器（LINKER_LANGUAGE CXX）链接，否则 ld.lld 报未定义 C++ runtime 符号。
project(test_ladybug LANGUAGES C CXX)

# ladybug 的 package_info 声明了 cpp_info.requires=openssl::openssl，
# CMakeDeps 会通过 ladybug::ladybug 传递依赖；此处再显式 find 以链接
# OpenSSL 静态库（liblbug.a 引用 EVP_*/BIO_* 符号）。
find_package(ladybug CONFIG REQUIRED)
find_package(openssl CONFIG REQUIRED)

add_executable(test_ladybug test.c)
target_link_libraries(test_ladybug PRIVATE ladybug::ladybug openssl::openssl)
# 强制 C++ 链接器驱动（自动带入 libc++/libc++abi 运行时）
set_target_properties(test_ladybug PROPERTIES LINKER_LANGUAGE CXX)
# OHOS: liblbug.a 引用 std::format_error（在 libc++experimental.a），
# 即使 package_info 已声明 system_libs，这里再兜底一次，保证链接顺序正确。
if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
    target_link_options(test_ladybug PRIVATE -lc++experimental)
endif()

# AI 补充上游测试用例（规则 4 技术论证，2026-08-22）：
# 覆盖上游 value/data_type/query_result/prepared_statement/聚合/DDL/DML/
# 过滤/事务/版本 共 10 大场景，通过 C API + Cypher 在 OHOS 上真实执行。
add_executable(test_ai test_ai.c)
target_link_libraries(test_ai PRIVATE ladybug::ladybug openssl::openssl)
set_target_properties(test_ai PROPERTIES LINKER_LANGUAGE CXX)
if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
    target_link_options(test_ai PRIVATE -lc++experimental)
endif()
