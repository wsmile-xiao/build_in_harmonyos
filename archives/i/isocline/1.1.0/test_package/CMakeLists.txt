cmake_minimum_required(VERSION 3.15)
project(test_isocline C)

find_package(isocline REQUIRED CONFIG)

add_executable(test_isocline test_isocline.c)
target_link_libraries(test_isocline PRIVATE isocline::isocline)

enable_testing()
add_test(NAME test_isocline COMMAND test_isocline)
