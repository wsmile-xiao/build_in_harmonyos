cmake_minimum_required(VERSION 3.15)
project(test_kcodecs CXX)

find_package(KF6Codecs REQUIRED)

add_executable(test_kcodecs test.cpp)
target_link_libraries(test_kcodecs KF6::Codecs)

enable_testing()
add_test(NAME test_kcodecs COMMAND test_kcodecs)
