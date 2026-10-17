cmake_minimum_required(VERSION 3.15)
project(test_libvpd C CXX)

set(CMAKE_C_STANDARD 99)
set(CMAKE_CXX_STANDARD 11)

# libvpd 的 cpp_info 是扁平的（无 components），CMakeDeps 只生成一个
# libvpd::libvpd 目标，其中已包含 vpd 与 vpd_cxx 两个库
find_package(libvpd REQUIRED)
# 公开头文件 vpddbenv.h 直接 #include <sqlite3.h>，消费者需自行提供该头文件
find_package(sqlite3 REQUIRED)

add_executable(test_libvpd_c test_libvpd.c)
target_link_libraries(test_libvpd_c PRIVATE libvpd::libvpd sqlite3::sqlite3)

# C++ 消费者用例：验证包内 libvpd_cxx.a 可被链接与调用。
# 配方 package_info 声明 libs = ["vpd", "vpd_cxx"]，但 C 用例只触及 C API，
# 若无本目标则 libvpd_cxx 随包发布却从未被实际使用验证过。
add_executable(test_libvpd_cxx test_libvpd_cxx.cpp)
target_link_libraries(test_libvpd_cxx PRIVATE libvpd::libvpd sqlite3::sqlite3)

# 鸿蒙专有用例：断言只在 OHOS 平台才有意义的前提（__OHOS__ 编译期定义、
# 运行期 sysname=HarmonyOS/aarch64、libc++ 而非 libstdc++、静态链接产物可用）。
# 前两个用例是通用消费者验证，本目标专测本次适配赖以成立的平台假设。
add_executable(test_libvpd_ohos test_libvpd_ohos.cpp)
target_link_libraries(test_libvpd_ohos PRIVATE libvpd::libvpd sqlite3::sqlite3)

enable_testing()
add_test(NAME test_libvpd_c COMMAND test_libvpd_c)
add_test(NAME test_libvpd_cxx COMMAND test_libvpd_cxx)
add_test(NAME test_libvpd_ohos COMMAND test_libvpd_ohos)
