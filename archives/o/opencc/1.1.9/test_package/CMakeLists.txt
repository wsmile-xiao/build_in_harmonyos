cmake_minimum_required(VERSION 3.15)
project(test_opencc CXX)

set(CMAKE_CXX_STANDARD 14)

find_package(opencc REQUIRED)

add_executable(test_opencc test.cpp)
target_link_libraries(test_opencc opencc::opencc)

enable_testing()
add_test(NAME test_opencc COMMAND test_opencc)
