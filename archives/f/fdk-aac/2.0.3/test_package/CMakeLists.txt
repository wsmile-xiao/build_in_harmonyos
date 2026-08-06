cmake_minimum_required(VERSION 3.15)
project(test_fdk_aac C)

find_package(fdk-aac CONFIG REQUIRED)

add_executable(test_fdk-aac test.c)
target_link_libraries(test_fdk-aac fdk-aac::fdk-aac)

enable_testing()
add_test(NAME test_fdk-aac COMMAND test_fdk-aac)
