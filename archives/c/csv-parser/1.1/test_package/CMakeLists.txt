cmake_minimum_required(VERSION 3.15)
project(test_csv-parser CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(csv-parser REQUIRED)

add_executable(test_csv-parser test.cpp)
target_link_libraries(test_csv-parser csv-parser::csv-parser)

enable_testing()
add_test(NAME test_csv-parser COMMAND test_csv-parser)
