cmake_minimum_required(VERSION 3.15)
project(test_flac C)

find_package(FLAC REQUIRED)

add_executable(test_flac test.c)
target_link_libraries(test_flac FLAC::FLAC)

enable_testing()
add_test(NAME test_flac COMMAND test_flac)
