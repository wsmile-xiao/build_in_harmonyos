cmake_minimum_required(VERSION 3.16)
project(test_qhull LANGUAGES C)

find_package(Qhull CONFIG REQUIRED)

add_executable(test_qhull test.c)
target_compile_features(test_qhull PRIVATE c_std_11)
target_link_libraries(test_qhull PRIVATE Qhull::qhull_r)
