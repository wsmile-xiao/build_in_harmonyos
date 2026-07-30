cmake_minimum_required(VERSION 3.15)
project(test_bento4 CXX)

find_package(bento4 REQUIRED)

add_executable(test_bento4 test.cpp)
target_link_libraries(test_bento4 bento4::bento4)

enable_testing()
add_test(NAME test_bento4 COMMAND test_bento4)
