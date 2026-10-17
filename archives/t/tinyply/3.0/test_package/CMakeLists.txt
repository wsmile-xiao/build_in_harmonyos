cmake_minimum_required(VERSION 3.15)
project(test_tinyply CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(tinyply REQUIRED)

add_executable(test_tinyply test.cpp)
target_link_libraries(test_tinyply PRIVATE tinyply::tinyply)

enable_testing()
add_test(NAME test_tinyply COMMAND test_tinyply)
