cmake_minimum_required(VERSION 3.15)
project(test_cbc LANGUAGES CXX)

find_package(cbc CONFIG REQUIRED)

# 消费者冒烟测试：链接 cbc 并求解一个小 MILP（R34：实质调用 API）
add_executable(test_cbc test_cbc.cpp)
target_link_libraries(test_cbc PRIVATE cbc::cbc)

# HarmonyOS 专项测试：通过公开 C 接口建模 0-1 背包并断言最优值 14
add_executable(cbc_ohos_test cbc_ohos_test.cpp)
target_link_libraries(cbc_ohos_test PRIVATE cbc::cbc)

# 消费者用例：仅使用已安装公开头/公开 API，读取 MPS 并求解
add_executable(cbc_consumer cbc_consumer.cpp)
target_link_libraries(cbc_consumer PRIVATE cbc::cbc)

enable_testing()
add_test(NAME cbc_smoke COMMAND test_cbc)
add_test(NAME cbc_ohos COMMAND cbc_ohos_test)
add_test(NAME cbc_consumer COMMAND cbc_consumer)