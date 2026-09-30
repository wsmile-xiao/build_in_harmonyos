cmake_minimum_required(VERSION 3.15)
project(test_fast_zlib C)

# Find the package via Conan-generated CMakeDeps
find_package(fast_zlib REQUIRED)

# 消费者验证 (r01, R34): 公开 zlib.h API compress2/uncompress 往返
add_executable(test_fast_zlib test.c)
target_link_libraries(test_fast_zlib fast_zlib::fast_zlib)
enable_testing()
add_test(NAME test_fast_zlib COMMAND test_fast_zlib)

# HarmonyOS 专项测试 (r02 新增, 硬门禁): 快速匹配符号 + 流式 API + OHOS aarch64 往返
add_executable(ohos_specific_test ohos_specific_test.c)
target_link_libraries(ohos_specific_test fast_zlib::fast_zlib)
add_test(NAME ohos_specific_test COMMAND ohos_specific_test)