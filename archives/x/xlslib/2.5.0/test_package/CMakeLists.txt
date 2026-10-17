cmake_minimum_required(VERSION 3.15)
project(test_xlslib LANGUAGES CXX)

find_package(xlslib CONFIG REQUIRED)

add_executable(test_xlslib test_xlslib.cpp)
target_link_libraries(test_xlslib PRIVATE xlslib::xlslib)

enable_testing()
add_test(NAME test_xlslib COMMAND test_xlslib)
