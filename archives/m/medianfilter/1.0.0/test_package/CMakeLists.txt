cmake_minimum_required(VERSION 3.15)
project(medianfilter_test_package C CXX)

find_package(medianfilter CONFIG REQUIRED)

add_executable(test_medianfilter_c test_medianfilter_c.c)
target_link_libraries(test_medianfilter_c PRIVATE medianfilter::medianfilter)

add_executable(test_medianfilter_cpp test_medianfilter_cpp.cpp)
target_link_libraries(test_medianfilter_cpp PRIVATE medianfilter::medianfilter)

enable_testing()
add_test(NAME c_api COMMAND test_medianfilter_c)
add_test(NAME cpp_template COMMAND test_medianfilter_cpp)
