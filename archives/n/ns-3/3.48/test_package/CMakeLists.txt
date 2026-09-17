cmake_minimum_required(VERSION 3.15)
project(test_ns3 CXX)

# ns-3 3.48 的公共头文件使用 C++20 特性（std::remove_cvref_t / operator<=> 等），
# 消费者同样必须以 C++20 编译，否则包含 ns3/*-module.h 即失败。
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 包名与 target 以 conanfile.py 的 package_info() 为准：
#   cmake_file_name = "ns3", cmake_target_name = "ns3::core"
# （与 ns-3 上游 CMake 包的命名一致）。CMakeDeps 生成 ns3-config.cmake。
find_package(ns3 REQUIRED)

add_executable(test_ns3 test_ns3.cc)
target_link_libraries(test_ns3 ns3::core)

enable_testing()
add_test(NAME test_ns3 COMMAND test_ns3)
