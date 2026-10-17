cmake_minimum_required(VERSION 3.15)
project(test_shine C)

find_package(shine REQUIRED)

add_executable(test_shine test.c)
target_link_libraries(test_shine PRIVATE shine::shine m)
target_compile_features(test_shine PRIVATE c_std_99)
# strict compilation: implicit declarations (e.g. sin without <math.h>)
# must fail, not silently truncate
target_compile_options(test_shine PRIVATE -std=c99 -Werror)

enable_testing()
add_test(NAME test_shine COMMAND test_shine)
