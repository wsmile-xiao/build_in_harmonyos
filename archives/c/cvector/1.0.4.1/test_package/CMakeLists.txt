cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(cvector CONFIG REQUIRED)

add_executable(test_cvector test_cvector.c)
target_link_libraries(test_cvector PRIVATE cvector::cvector)
target_compile_features(test_cvector PRIVATE c_std_99)
