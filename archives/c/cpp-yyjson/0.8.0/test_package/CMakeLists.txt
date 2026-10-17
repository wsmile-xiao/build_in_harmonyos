cmake_minimum_required(VERSION 3.16)
project(test_cpp-yyjson CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps.
# 上游 CMakeLists.txt 安装的 config 名为 cpp_yyjsonConfig.cmake（PROJECT_NAME 为 cpp_yyjson）
find_package(cpp_yyjson CONFIG REQUIRED)

add_executable(test_cpp-yyjson test.cpp)
target_link_libraries(test_cpp-yyjson cpp_yyjson::cpp_yyjson)

# HarmonyOS 专项测试：额外消费者用例，验证 OHOS libc++15 能力守卫回退路径
add_executable(test_ohos_special test_ohos_special.cpp)
target_link_libraries(test_ohos_special cpp_yyjson::cpp_yyjson)

enable_testing()
add_test(NAME test_cpp-yyjson COMMAND test_cpp-yyjson)
add_test(NAME test_ohos_special COMMAND test_ohos_special)
