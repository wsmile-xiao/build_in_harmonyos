cmake_minimum_required(VERSION 3.15)
project(libewf_test LANGUAGES C)

find_package(libewf CONFIG REQUIRED)

add_executable(test_libewf test_libewf.c)
target_link_libraries(test_libewf PRIVATE libewf::libewf)

enable_testing()
add_test(NAME test_libewf COMMAND test_libewf)
