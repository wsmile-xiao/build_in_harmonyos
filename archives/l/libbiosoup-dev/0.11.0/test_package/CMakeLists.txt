cmake_minimum_required(VERSION 3.15)
project(test_biosoup CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(biosoup REQUIRED)

add_executable(test_biosoup test_biosoup.cpp)
target_link_libraries(test_biosoup PRIVATE biosoup::biosoup)

enable_testing()
add_test(NAME test_biosoup COMMAND test_biosoup)
