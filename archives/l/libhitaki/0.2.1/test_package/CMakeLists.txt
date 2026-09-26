cmake_minimum_required(VERSION 3.15)
project(test_libhitaki C)

# Find the package via Conan-generated CMakeDeps
find_package(libhitaki REQUIRED)

# 消费者用例：仅通过公开头文件/API 使用本库
add_executable(test_libhitaki test.c)
# 需要 glib/gobject 头与库（hitaki.h 包含 glib.h），由 libhitaki::libhitaki
# 的传递依赖（glib2::glib2，transitive_headers）提供
target_link_libraries(test_libhitaki libhitaki::libhitaki)

# HarmonyOS 专项测试：无 GIR typelib 环境下公开符号与类型系统回归
add_executable(test_libhitaki_ohos test_ohos.c)
target_link_libraries(test_libhitaki_ohos libhitaki::libhitaki ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_libhitaki COMMAND test_libhitaki)
add_test(NAME test_libhitaki_ohos COMMAND test_libhitaki_ohos)