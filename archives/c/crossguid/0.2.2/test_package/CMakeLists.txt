cmake_minimum_required(VERSION 3.5.1)
project(test_crossguid LANGUAGES CXX)

find_package(crossguid CONFIG REQUIRED)

add_executable(test_crossguid test_crossguid.cpp)
target_link_libraries(test_crossguid PRIVATE crossguid::crossguid)

# HarmonyOS 专项测试：真实行为验证（批量唯一性/字节往返/swap/错误输入）
add_executable(test_ohos_crossguid test_ohos_crossguid.cpp)
target_link_libraries(test_ohos_crossguid PRIVATE crossguid::crossguid)