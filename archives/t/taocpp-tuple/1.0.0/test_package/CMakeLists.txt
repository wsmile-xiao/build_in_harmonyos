cmake_minimum_required(VERSION 3.15)
project(test_taocpp_tuple CXX)

find_package(taocpp-tuple CONFIG REQUIRED)

# 消费者测试（R34：实质调用公开 API）
add_executable(test_taocpp_tuple test.cpp)
target_link_libraries(test_taocpp_tuple PRIVATE taocpp::tuple)
set_target_properties(test_taocpp_tuple PROPERTIES CXX_STANDARD 11 CXX_STANDARD_REQUIRED ON)

# HarmonyOS 专项测试（OHOS 工具链真实运行，独立于上游用例）
add_executable(test_ohos test_ohos.cpp)
target_link_libraries(test_ohos PRIVATE taocpp::tuple)
set_target_properties(test_ohos PROPERTIES CXX_STANDARD 14 CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_taocpp_tuple COMMAND test_taocpp_tuple)
add_test(NAME test_ohos COMMAND test_ohos)
