cmake_minimum_required(VERSION 3.15)
project(test_toml11 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(toml11 REQUIRED)

add_executable(test_toml11 src/main.cpp)
target_link_libraries(test_toml11 toml11::toml11)

enable_testing()
add_test(NAME toml11_test COMMAND test_toml11)
