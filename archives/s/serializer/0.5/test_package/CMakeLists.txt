cmake_minimum_required(VERSION 3.15)
project(serializer_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(serializer CONFIG REQUIRED)

add_executable(serializer_test test.cpp)
target_link_libraries(serializer_test PRIVATE serializer::serializer)

# HarmonyOS 专项测试：OHOS 平台特有行为（端序/布局、size_is、optional/variant、polymorphic id）
add_executable(ohos_test ohos_test.cpp)
target_link_libraries(ohos_test PRIVATE serializer::serializer)

enable_testing()
add_test(NAME serializer_test COMMAND serializer_test)
add_test(NAME ohos_test COMMAND ohos_test)
