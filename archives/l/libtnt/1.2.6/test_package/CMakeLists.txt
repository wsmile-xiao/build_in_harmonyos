cmake_minimum_required(VERSION 3.16)
project(libtnt_test_package CXX)

find_package(libtnt REQUIRED CONFIG)

# 组件冒烟：9 类核心 API 数值断言（32 项）
add_executable(test_libtnt test_libtnt.cpp)
target_link_libraries(test_libtnt PRIVATE libtnt::libtnt)

# 消费者用例：马尔可夫链稳态幂迭代 + 加权平均（6 项断言）
add_executable(test_consumer test_consumer.cpp)
target_link_libraries(test_consumer PRIVATE libtnt::libtnt)

# 鸿蒙特有测试：musl clock() 时钟路径 + 真机堆跨页大数组 + aarch64 FPU 语义（6 项断言）
add_executable(test_ohos test_ohos.cpp)
target_link_libraries(test_ohos PRIVATE libtnt::libtnt)

# CI profile cppstd=17；TNT（C++98 模板库）在 C++17 下编译通过，
# 与 test_package/conanfile.py 的 CMAKE_CXX_STANDARD 注入保持一致
set_target_properties(test_libtnt test_consumer test_ohos PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON CXX_EXTENSIONS OFF)

# OHOS：测试二进制静态链接 libc++ 运行时（-static-libstdc++），
# 运行时不依赖 LD_LIBRARY_PATH 指向 SDK 的 libc++_shared.so——
# conanrun 环境不含 profile buildenv 的 SDK 库路径，动态链接会导致
# "Error loading shared library libc++_shared.so" (rc=127)。
# 注意：target_link_options 不支持一次传多目标（与 set_target_properties 不同）
target_link_options(test_libtnt PRIVATE -static-libstdc++)
target_link_options(test_consumer PRIVATE -static-libstdc++)
target_link_options(test_ohos PRIVATE -static-libstdc++)

enable_testing()
add_test(NAME libtnt_smoke COMMAND test_libtnt)
add_test(NAME libtnt_consumer COMMAND test_consumer)
add_test(NAME libtnt_ohos COMMAND test_ohos)
