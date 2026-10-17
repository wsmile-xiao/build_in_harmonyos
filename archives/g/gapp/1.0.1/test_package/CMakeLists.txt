cmake_minimum_required(VERSION 3.16)
project(test_gapp CXX)

find_package(gapp REQUIRED)

add_executable(test_gapp test_gapp.cpp)
target_link_libraries(test_gapp PRIVATE gapp::gapp)
target_compile_features(test_gapp PRIVATE cxx_std_20)

enable_testing()
add_test(NAME test_gapp COMMAND test_gapp)
