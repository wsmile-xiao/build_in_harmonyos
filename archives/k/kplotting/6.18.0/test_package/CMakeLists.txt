cmake_minimum_required(VERSION 3.16)
project(test_kplotting LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS Widgets)
find_package(KF6Plotting 6.18.0 REQUIRED)

add_executable(test_kplotting test.cpp)
target_link_libraries(test_kplotting PRIVATE Qt6::Widgets KF6::Plotting)

enable_testing()
add_test(NAME test_kplotting COMMAND test_kplotting)
