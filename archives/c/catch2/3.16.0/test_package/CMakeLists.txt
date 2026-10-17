cmake_minimum_required(VERSION 3.15)
project(test_catch2 LANGUAGES CXX)

find_package(Catch2 CONFIG REQUIRED)

add_executable(test_catch2 test_catch2.cpp)
target_compile_features(test_catch2 PRIVATE cxx_std_14)
target_link_libraries(test_catch2 PRIVATE Catch2::Catch2WithMain)

enable_testing()
add_test(NAME test_catch2 COMMAND test_catch2)
