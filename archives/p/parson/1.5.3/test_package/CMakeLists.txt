cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(parson CONFIG REQUIRED)

add_executable(test_parson test_parson.c)
target_link_libraries(test_parson PRIVATE parson::parson)
target_compile_features(test_parson PRIVATE c_std_99)
