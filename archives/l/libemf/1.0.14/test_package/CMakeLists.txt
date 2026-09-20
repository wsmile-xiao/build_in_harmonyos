cmake_minimum_required(VERSION 3.15)
project(test_libemf C)

enable_testing()

find_package(libemf REQUIRED)

add_executable(test_libemf_api test_libemf_api.c)
target_link_libraries(test_libemf_api libemf::libemf)

add_test(NAME test_libemf_api COMMAND test_libemf_api)
