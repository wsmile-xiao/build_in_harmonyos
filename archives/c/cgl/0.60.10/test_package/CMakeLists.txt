cmake_minimum_required(VERSION 3.15)
project(test_cgl LANGUAGES CXX)

find_package(cgl CONFIG REQUIRED)
add_executable(test_cgl test.cpp)
target_link_libraries(test_cgl PRIVATE cgl::cgl)
enable_testing()
add_test(NAME cgl_smoke COMMAND test_cgl)
