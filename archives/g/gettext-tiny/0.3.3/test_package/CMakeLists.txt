cmake_minimum_required(VERSION 3.15)
project(test_gettext-tiny C)

# Find the package via Conan-generated CMakeDeps
find_package(gettext-tiny REQUIRED)

# 强制调用真实 libintl 函数（libintl.h 默认宏展开 gettext()，需 LIBINTL_NO_MACROS）
add_executable(test_gettext-tiny test.c)
target_compile_definitions(test_gettext-tiny PRIVATE LIBINTL_NO_MACROS=1)
target_link_libraries(test_gettext-tiny gettext-tiny::gettext-tiny)

# HarmonyOS 专项测试：libintl 公开 API + msgfmt .mo 编译
# msgfmt 位于包内 bin 目录（PACKAGE_FOLDER 一定非空；library 类型包的 BIN_DIRS 可能为空），
# .po 在测试源目录，.mo 输出到构建目录 —— 全部编译期注入，不依赖运行时环境变量
set(GT_BIN_DIR "${gettext-tiny_PACKAGE_FOLDER_RELEASE}/bin")
add_executable(harmonyos_specific_test harmonyos_specific_test.c)
target_compile_definitions(harmonyos_specific_test PRIVATE
    LIBINTL_NO_MACROS=1
    GT_BIN_DIR="${GT_BIN_DIR}"
    GT_PO_DIR="${CMAKE_CURRENT_SOURCE_DIR}"
    GT_TMP_DIR="${CMAKE_CURRENT_BINARY_DIR}")
target_link_libraries(harmonyos_specific_test gettext-tiny::gettext-tiny)

enable_testing()
add_test(NAME test_gettext-tiny COMMAND test_gettext-tiny)
add_test(NAME harmonyos_specific_test COMMAND harmonyos_specific_test)
