cmake_minimum_required(VERSION 3.15)
project(test_onednn LANGUAGES C)

find_package(dnnl REQUIRED)

add_executable(test_onednn test.c)
target_link_libraries(test_onednn PRIVATE dnnl::dnnl)

enable_testing()
add_test(NAME test_onednn COMMAND test_onednn)
