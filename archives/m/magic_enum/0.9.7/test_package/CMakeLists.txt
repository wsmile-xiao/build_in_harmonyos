cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(magic_enum REQUIRED)

add_executable(test_magic_enum test_magic_enum.cpp)
target_link_libraries(test_magic_enum PRIVATE magic_enum::magic_enum)
set_property(TARGET test_magic_enum PROPERTY CXX_STANDARD 17)
set_property(TARGET test_magic_enum PROPERTY CXX_STANDARD_REQUIRED ON)

# 鸿蒙特有测试：验证 magic_enum 在 OHOS aarch64 上的真实兼容行为
add_executable(test_magic_enum_ohos test_magic_enum_ohos.cpp)
target_link_libraries(test_magic_enum_ohos PRIVATE magic_enum::magic_enum)
set_property(TARGET test_magic_enum_ohos PROPERTY CXX_STANDARD 17)
set_property(TARGET test_magic_enum_ohos PROPERTY CXX_STANDARD_REQUIRED ON)