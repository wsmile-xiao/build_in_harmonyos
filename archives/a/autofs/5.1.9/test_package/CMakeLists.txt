cmake_minimum_required(VERSION 3.15)
project(test_autofs C)

add_executable(test_autofs test.c)
# The test uses dlopen() directly and does not link against libautofs.
target_link_libraries(test_autofs ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_autofs COMMAND test_autofs)