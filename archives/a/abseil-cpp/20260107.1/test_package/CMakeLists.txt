cmake_minimum_required(VERSION 3.15)
project(test_abseil_cpp LANGUAGES CXX)

find_package(abseil-cpp CONFIG REQUIRED)

add_executable(test_abseil_cpp test.cpp)
target_compile_features(test_abseil_cpp PRIVATE cxx_std_17)
target_link_libraries(test_abseil_cpp PRIVATE abseil-cpp::abseil-cpp)

enable_testing()
add_test(NAME test_abseil_cpp COMMAND test_abseil_cpp)
