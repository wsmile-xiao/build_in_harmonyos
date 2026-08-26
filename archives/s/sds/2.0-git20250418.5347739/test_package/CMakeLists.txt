cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(sds CONFIG REQUIRED)

add_executable(test_sds test_sds.c)
target_link_libraries(test_sds PRIVATE sds::sds)
target_compile_features(test_sds PRIVATE c_std_99)
