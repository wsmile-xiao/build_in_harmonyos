cmake_minimum_required(VERSION 3.15)
project(test_zarchive CXX)

find_package(zarchive REQUIRED)

add_executable(test_zarchive test_zarchive.cpp)
target_link_libraries(test_zarchive PRIVATE ZArchive::zarchive)

enable_testing()
add_test(NAME test_zarchive COMMAND test_zarchive)
