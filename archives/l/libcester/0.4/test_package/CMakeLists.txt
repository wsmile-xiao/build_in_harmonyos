cmake_minimum_required(VERSION 3.15)
project(test_libcester C)

# OHOS musl libc 的 stdio.h 仅在 __STDC_VERSION__ < 201112L（C99 及以下）时
# 提供 struct _IO_FILE 占位定义；clang 默认 gnu17 下 FILE 为不透明类型，
# cester.h 因含 FILE 按值字段无法编译。按上游 test/CMakeLists.txt 的
# -ansi 同语义强制 C99（与上游编译口径一致）。
set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)

# 通过 Conan CMakeDeps 查找 libcester 包（公开头文件接口）
find_package(libcester REQUIRED)

add_executable(test_libcester test.c)
target_link_libraries(test_libcester libcester::libcester)

# 鸿蒙专项测试：验证 cester.h 在 OHOS 工具链/运行时下的编译链接与断言行为
add_executable(test_libcester_ohos test_ohos.c)
target_link_libraries(test_libcester_ohos libcester::libcester)

enable_testing()
add_test(NAME test_libcester COMMAND test_libcester)
add_test(NAME test_libcester_ohos COMMAND test_libcester_ohos)
