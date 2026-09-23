cmake_minimum_required(VERSION 3.15)
project(test_libatomic_ops C)

find_package(libatomic-ops REQUIRED)

add_executable(test_libatomic_ops test.c)
target_link_libraries(test_libatomic_ops libatomic-ops::libatomic-ops)

enable_testing()
add_test(NAME test_libatomic_ops COMMAND test_libatomic_ops)
