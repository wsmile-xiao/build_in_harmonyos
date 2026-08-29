cmake_minimum_required(VERSION 3.15)
project(test_logc C)

find_package(log.c CONFIG REQUIRED)

add_executable(test_logc test.c)
target_link_libraries(test_logc PRIVATE log.c::log.c)
target_compile_features(test_logc PRIVATE c_std_99)

enable_testing()
add_test(NAME test_logc COMMAND test_logc)
