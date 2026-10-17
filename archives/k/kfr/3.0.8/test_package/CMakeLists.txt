cmake_minimum_required(VERSION 3.15)
project(test_kfr CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(kfr REQUIRED)

add_executable(test_kfr test_kfr.cpp)
target_link_libraries(test_kfr kfr::kfr)

enable_testing()
add_test(NAME test_kfr COMMAND test_kfr)
