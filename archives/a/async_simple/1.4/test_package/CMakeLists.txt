cmake_minimum_required(VERSION 3.15)
project(test_async_simple CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(async_simple REQUIRED)

add_executable(test_async_simple src/main.cpp)
target_link_libraries(test_async_simple async_simple::async_simple)

enable_testing()
add_test(NAME test_async_simple COMMAND test_async_simple)
