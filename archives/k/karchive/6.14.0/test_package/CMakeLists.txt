cmake_minimum_required(VERSION 3.15)
project(test_karchive CXX)

find_package(KF6Archive REQUIRED)

add_executable(test_karchive test.cpp)
target_link_libraries(test_karchive KF6::Archive)

enable_testing()
add_test(NAME test_karchive COMMAND test_karchive)
