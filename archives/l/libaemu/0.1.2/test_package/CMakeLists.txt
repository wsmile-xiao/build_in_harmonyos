cmake_minimum_required(VERSION 3.15)
project(test_libaemu CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(libaemu REQUIRED)

add_executable(test_libaemu test_libaemu.cpp)
target_link_libraries(test_libaemu PRIVATE libaemu::libaemu)

enable_testing()
add_test(NAME test_libaemu COMMAND test_libaemu)
