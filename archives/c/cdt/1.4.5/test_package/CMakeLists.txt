cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(CDT REQUIRED)

# 消费者验证：真实调用 CDT 公开 API（非空壳测试）
add_executable(test_cdt test_package.cpp)
target_link_libraries(test_cdt PRIVATE CDT::CDT)

# HarmonyOS 专项测试：独立可执行 target（与 test_package 分离，
# 两个源文件各自含 main()，不得合并）。
add_executable(ohos_specific_test ohos_specific_test.cpp)
target_link_libraries(ohos_specific_test PRIVATE CDT::CDT)