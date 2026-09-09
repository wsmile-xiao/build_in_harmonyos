cmake_minimum_required(VERSION 3.15)
project(test_liquid_dsp C)

find_package(liquid CONFIG REQUIRED)

add_executable(test_liquid_dsp test.c)
target_link_libraries(test_liquid_dsp liquid::liquid-static)

enable_testing()
add_test(NAME test_liquid_dsp COMMAND test_liquid_dsp)
