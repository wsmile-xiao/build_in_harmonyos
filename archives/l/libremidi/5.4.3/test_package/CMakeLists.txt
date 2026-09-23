cmake_minimum_required(VERSION 3.15)
project(test_libremidi CXX)

find_package(libremidi CONFIG REQUIRED)

add_executable(test_libremidi test_libremidi.cpp)
# libremidi 的公开头文件（configurations.hpp / message.hpp 等）用了 std::span、concept、
# requires，消费方必须按 C++20 编译；CI 与真机 profile 默认是 cppstd=17，故这里显式抬到 20。
set_target_properties(test_libremidi PROPERTIES CXX_STANDARD 20 CXX_STANDARD_REQUIRED ON)
target_link_libraries(test_libremidi PRIVATE libremidi::libremidi)
