cmake_minimum_required(VERSION 3.15)
project(test_inih_inireader LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(inih-inireader CONFIG REQUIRED)

add_executable(test_inih_inireader test_inih_inireader.cpp)
target_link_libraries(test_inih_inireader PRIVATE inih-inireader::inih-inireader)

enable_testing()
add_test(NAME test_inih_inireader COMMAND test_inih_inireader)
