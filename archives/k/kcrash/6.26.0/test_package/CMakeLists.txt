cmake_minimum_required(VERSION 3.15)
project(test_kcrash CXX)

find_package(KF6Crash REQUIRED)

add_executable(test_kcrash test.cpp)
target_link_libraries(test_kcrash KF6::Crash)

enable_testing()
add_test(NAME test_kcrash COMMAND test_kcrash)
