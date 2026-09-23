cmake_minimum_required(VERSION 3.15)
project(test_boost1_84_serialization CXX)

set(CMAKE_CXX_STANDARD 17)

find_package(Boost REQUIRED CONFIG COMPONENTS serialization)

add_executable(test_boost1_84_serialization test_boost1_84_serialization.cpp)
target_link_libraries(test_boost1_84_serialization PRIVATE Boost::serialization)
# OHOS musl: 测试二进制静态链接 libc++（动态依赖 libc++_shared.so 在
# conan buildenv / CI 环境下因 LD_LIBRARY_PATH 解析问题加载失败 rc=127）。
# OHOS 适配版 conan 将 os=OHOS 映射为 CMAKE_SYSTEM_NAME=HarmonyOS。
if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    target_link_options(test_boost1_84_serialization PRIVATE -static-libstdc++)
endif()

enable_testing()
add_test(NAME boost1_84_serialization_test COMMAND test_boost1_84_serialization)
