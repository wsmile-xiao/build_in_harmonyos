cmake_minimum_required(VERSION 3.15)
project(test_reflect_cpp CXX)

# reflect-cpp 是 C++20-only；共享 ohos-aarch64 profile 声明 cppstd=17，
# 此处显式锁定 C++20（与库配方 generate() 中的 CMAKE_CXX_STANDARD=20 同口径）
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 通过 Conan 生成的 CMakeDeps 查找 reflect-cpp 包
find_package(reflectcpp REQUIRED)

add_executable(test_reflect_cpp test_reflect_cpp.cpp)
target_link_libraries(test_reflect_cpp PRIVATE reflectcpp::reflectcpp)

# HarmonyOS 专项测试：独立可执行目标
add_executable(harmonyos_specific_test harmonyos_specific_test.cpp)
target_link_libraries(harmonyos_specific_test PRIVATE reflectcpp::reflectcpp)

enable_testing()
add_test(NAME test_reflect_cpp COMMAND test_reflect_cpp)
add_test(NAME harmonyos_specific_test COMMAND harmonyos_specific_test)
