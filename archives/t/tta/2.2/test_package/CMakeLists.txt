cmake_minimum_required(VERSION 3.15)
project(test_tta LANGUAGES C)

find_package(tta CONFIG REQUIRED)

add_executable(test_tta test.c)
target_link_libraries(test_tta PRIVATE tta::tta)
target_compile_features(test_tta PRIVATE c_std_99)
target_compile_options(test_tta PRIVATE -Wall -Wextra)
