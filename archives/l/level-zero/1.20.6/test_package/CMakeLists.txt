cmake_minimum_required(VERSION 3.15)
project(test_level_zero LANGUAGES CXX)

find_package(level-zero CONFIG REQUIRED)

add_executable(test_level_zero test.cpp)
target_compile_features(test_level_zero PRIVATE cxx_std_14)
target_link_libraries(test_level_zero PRIVATE level-zero::level-zero)

enable_testing()
add_test(NAME test_level_zero COMMAND test_level_zero)
