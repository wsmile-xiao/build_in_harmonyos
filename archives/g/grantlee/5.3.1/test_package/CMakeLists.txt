cmake_minimum_required(VERSION 3.15)
project(test_grantlee CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(Grantlee5 REQUIRED)
find_package(Qt5Core REQUIRED)

add_executable(test_grantlee test_grantlee.cpp)
target_link_libraries(test_grantlee Grantlee5::Templates Qt5::Core)

enable_testing()
add_test(NAME test_grantlee COMMAND test_grantlee)
