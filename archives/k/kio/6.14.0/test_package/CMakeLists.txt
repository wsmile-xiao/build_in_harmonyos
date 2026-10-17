cmake_minimum_required(VERSION 3.15)
project(test_kio CXX)

find_package(KF6KIO REQUIRED)

add_executable(test_kio test.cpp)
target_link_libraries(test_kio KF6::KIOCore)

enable_testing()
add_test(NAME test_kio COMMAND test_kio)
