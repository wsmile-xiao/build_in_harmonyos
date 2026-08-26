cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(tinyexpr CONFIG REQUIRED)

add_executable(test_tinyexpr test_tinyexpr.c)
target_link_libraries(test_tinyexpr PRIVATE tinyexpr::tinyexpr)
target_compile_features(test_tinyexpr PRIVATE c_std_99)
