cmake_minimum_required(VERSION 3.15)
project(test_libxtst C)

find_package(libxtst REQUIRED)

add_executable(test_libxtst test.c)
target_link_libraries(test_libxtst PRIVATE libxtst::libxtst)

enable_testing()
add_test(NAME test_libxtst COMMAND test_libxtst)
