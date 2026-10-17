cmake_minimum_required(VERSION 3.15)
project(test_yoga CXX)

set(CMAKE_CXX_STANDARD 20)

find_package(yoga REQUIRED)

add_executable(test_yoga test.cpp)
target_link_libraries(test_yoga yoga::yoga)

enable_testing()
add_test(NAME test_yoga COMMAND test_yoga)
