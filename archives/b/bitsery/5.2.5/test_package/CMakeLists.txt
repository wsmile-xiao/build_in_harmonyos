cmake_minimum_required(VERSION 3.15)
project(test_bitsery CXX)

find_package(Bitsery REQUIRED)

add_executable(test_bitsery test_bitsery.cpp)
target_link_libraries(test_bitsery Bitsery::bitsery)

enable_testing()
add_test(NAME test_bitsery COMMAND test_bitsery)
