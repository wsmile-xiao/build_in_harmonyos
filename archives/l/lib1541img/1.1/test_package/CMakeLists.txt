cmake_minimum_required(VERSION 3.15)
project(test_1541img C)

find_package(1541img REQUIRED)

add_executable(test_1541img test_1541img.c)
target_link_libraries(test_1541img PRIVATE 1541img::1541img)
target_compile_definitions(test_1541img PRIVATE STATIC_1541IMG)

enable_testing()
add_test(NAME test_1541img COMMAND test_1541img)
