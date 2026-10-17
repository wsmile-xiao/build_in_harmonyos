cmake_minimum_required(VERSION 3.16)
project(test_syndication LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Qt6 6.9.0 REQUIRED COMPONENTS Core)
find_package(KF6Syndication 6.18.0 REQUIRED)

add_executable(test_syndication test.cpp)
target_link_libraries(test_syndication PRIVATE Qt6::Core KF6::Syndication)

enable_testing()
add_test(NAME test_syndication COMMAND test_syndication)
