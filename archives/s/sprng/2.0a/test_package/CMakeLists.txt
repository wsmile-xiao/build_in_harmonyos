cmake_minimum_required(VERSION 3.15)
project(sprng_test C)

find_package(sprng REQUIRED CONFIG)

add_executable(test_sprng test.c)
target_link_libraries(test_sprng PRIVATE sprng::sprng)

enable_testing()
add_test(NAME test_sprng COMMAND test_sprng)
