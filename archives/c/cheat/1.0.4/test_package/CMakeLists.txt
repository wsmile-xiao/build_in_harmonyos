cmake_minimum_required(VERSION 3.15)
project(test_cheat C)

find_package(cheat REQUIRED)

add_executable(test_cheat test.c)
target_link_libraries(test_cheat PRIVATE cheat::cheat)

# 鸿蒙专项测试（独立于上游与普通消费者测试）
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos PRIVATE cheat::cheat)
