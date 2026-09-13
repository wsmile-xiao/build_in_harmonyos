cmake_minimum_required(VERSION 3.15)
project(test_cpp_lazy LANGUAGES CXX)

find_package(cpp-lazy 9.0.1 CONFIG REQUIRED)

add_executable(test_cpp_lazy test.cpp)
target_link_libraries(test_cpp_lazy PRIVATE cpp-lazy::cpp-lazy)
target_compile_features(test_cpp_lazy PRIVATE cxx_std_17)

include(CTest)
add_test(NAME test_cpp_lazy COMMAND test_cpp_lazy)
