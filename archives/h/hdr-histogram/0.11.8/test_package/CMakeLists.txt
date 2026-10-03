cmake_minimum_required(VERSION 3.15)
project(test_hdr_histogram C)

find_package(hdr_histogram REQUIRED)

add_executable(test_hdr_histogram test.c)
target_link_libraries(test_hdr_histogram hdr_histogram::hdr_histogram)

# HarmonyOS 专项测试：验证 OHOS 时间 API、原子并发记录与累积/百分位
add_executable(test_ohos_platform test_ohos_platform.c)
target_link_libraries(test_ohos_platform hdr_histogram::hdr_histogram)

enable_testing()
add_test(NAME test_hdr_histogram COMMAND test_hdr_histogram)
add_test(NAME test_ohos_platform COMMAND test_ohos_platform)
