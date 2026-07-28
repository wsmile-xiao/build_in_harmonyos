cmake_minimum_required(VERSION 3.15)
project(test_cereal CXX)

find_package(cereal REQUIRED)

add_executable(test_cereal test.cpp)
target_link_libraries(test_cereal PRIVATE cereal::cereal)
target_compile_features(test_cereal PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_cereal COMMAND test_cereal)
