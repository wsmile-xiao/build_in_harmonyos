cmake_minimum_required(VERSION 3.15)
project(supernovas_test_package LANGUAGES C CXX)

find_package(supernovas REQUIRED CONFIG)

add_executable(test_supernovas_c test_supernovas.c)
target_link_libraries(test_supernovas_c PRIVATE supernovas::core)
target_compile_features(test_supernovas_c PRIVATE c_std_99)

add_executable(test_supernovas_cpp test_supernovas.cpp)
target_link_libraries(test_supernovas_cpp PRIVATE supernovas::cpp)
target_compile_features(test_supernovas_cpp PRIVATE cxx_std_11)
