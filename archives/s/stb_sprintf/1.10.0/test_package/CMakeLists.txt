cmake_minimum_required(VERSION 3.15)
project(test_stb_sprintf C)

find_package(stb_sprintf CONFIG REQUIRED)

add_executable(test_stb_sprintf test_stb_sprintf.c)
target_link_libraries(test_stb_sprintf PRIVATE stb_sprintf::stb_sprintf)
target_compile_features(test_stb_sprintf PRIVATE c_std_99)

enable_testing()
add_test(NAME test_stb_sprintf COMMAND test_stb_sprintf)
