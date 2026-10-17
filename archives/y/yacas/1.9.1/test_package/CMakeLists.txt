cmake_minimum_required(VERSION 3.15)
project(test_yacas CXX)

find_package(yacas REQUIRED CONFIG)

add_executable(test_yacas test_yacas.cpp)
target_link_libraries(test_yacas PRIVATE yacas::yacas)

enable_testing()
add_test(NAME yacas_consumer COMMAND test_yacas)
