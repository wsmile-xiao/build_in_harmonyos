cmake_minimum_required(VERSION 3.15)
project(test_libsbml C)

find_package(libsbml REQUIRED)

add_executable(test_libsbml test_libsbml.c)
target_link_libraries(test_libsbml libsbml::libsbml)

enable_testing()
add_test(NAME test_libsbml COMMAND test_libsbml)
