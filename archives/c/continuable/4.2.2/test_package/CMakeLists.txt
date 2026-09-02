cmake_minimum_required(VERSION 3.11)
project(test_continuable LANGUAGES CXX)

enable_testing()

find_package(continuable CONFIG REQUIRED)

add_executable(test_continuable test_continuable.cpp)
target_compile_features(test_continuable PRIVATE cxx_std_14)
target_link_libraries(test_continuable PRIVATE continuable::continuable)

add_test(NAME test_continuable COMMAND test_continuable)
