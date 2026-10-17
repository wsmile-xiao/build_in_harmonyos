cmake_minimum_required(VERSION 3.15)
project(test_generic_serialization CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(GenericSerialization REQUIRED)

add_executable(test_generic_serialization test.cpp)
target_link_libraries(test_generic_serialization GenericSerialization::GenericSerialization)

# rule12 鸿蒙特有测试（独立入口，验证 OHOS 平台语义，与 test.cpp 去重）
add_executable(harmony_platform_test harmony_platform_test.cpp)
target_link_libraries(harmony_platform_test GenericSerialization::GenericSerialization)

enable_testing()
add_test(NAME test_generic_serialization COMMAND test_generic_serialization)
add_test(NAME harmony_platform_test COMMAND harmony_platform_test)
