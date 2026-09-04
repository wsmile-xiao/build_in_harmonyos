cmake_minimum_required(VERSION 3.15)
project(test_bullet CXX)

find_package(bullet REQUIRED)

add_executable(test_bullet test.cpp)
target_link_libraries(test_bullet bullet::bullet)

enable_testing()
add_test(NAME test_bullet COMMAND test_bullet)
