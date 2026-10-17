cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(YOMM2 CONFIG REQUIRED)

# 消费者验证：链接 libyomm2 并执行开放多方法分派（真实 API 调用，非空壳）。
add_executable(test_package test_package.cpp)
target_link_libraries(test_package YOMM2::yomm2)
target_compile_features(test_package PRIVATE cxx_std_17)

# HarmonyOS 专项测试：独立可执行 target（与 test_package 分离，
# 两个源文件各自含 main()，不得合并）。
add_executable(ohos_specific_test ohos_specific_test.cpp)
target_link_libraries(ohos_specific_test YOMM2::yomm2)
target_compile_features(ohos_specific_test PRIVATE cxx_std_17)