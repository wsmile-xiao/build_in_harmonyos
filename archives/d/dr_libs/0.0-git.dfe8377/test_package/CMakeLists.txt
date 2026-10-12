cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(dr_libs CONFIG REQUIRED)

add_executable(test_dr_libs test_dr_libs.c)
target_link_libraries(test_dr_libs PRIVATE dr_libs::dr_libs)
target_compile_features(test_dr_libs PRIVATE c_std_99)
