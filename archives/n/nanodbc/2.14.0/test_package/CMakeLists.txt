cmake_minimum_required(VERSION 3.15)
project(test_nanodbc LANGUAGES CXX)

find_package(nanodbc CONFIG REQUIRED)

add_executable(test_nanodbc test.cpp)
target_compile_features(test_nanodbc PRIVATE cxx_std_17)
target_link_libraries(test_nanodbc PRIVATE nanodbc::nanodbc)

enable_testing()
add_test(NAME test_nanodbc COMMAND test_nanodbc)
