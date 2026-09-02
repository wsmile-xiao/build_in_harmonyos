cmake_minimum_required(VERSION 3.15)
project(test_c4log CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(c4log REQUIRED CONFIG)

add_executable(test_c4log test.cpp)
target_link_libraries(test_c4log PRIVATE c4log::c4log)

# upstream doctest suite (5 TEST_CASEs) - reimplemented without doctest header
add_executable(test_c4log_upstream test_upstream.cpp)
target_link_libraries(test_c4log_upstream PRIVATE c4log::c4log)

enable_testing()
add_test(NAME test_c4log COMMAND test_c4log)
add_test(NAME test_c4log_upstream COMMAND test_c4log_upstream)
