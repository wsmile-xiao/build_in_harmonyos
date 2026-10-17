cmake_minimum_required(VERSION 3.15)
project(test_proj CXX)

find_package(PROJ REQUIRED)

add_executable(test_proj test_proj.cpp)
target_link_libraries(test_proj PRIVATE PROJ::proj)
set_target_properties(test_proj PROPERTIES CXX_STANDARD 11)

enable_testing()
add_test(NAME test_proj COMMAND test_proj)
