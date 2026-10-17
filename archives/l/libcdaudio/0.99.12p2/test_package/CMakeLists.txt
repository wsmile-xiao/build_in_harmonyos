cmake_minimum_required(VERSION 3.15)
project(test_libcdaudio C)

find_package(cdaudio REQUIRED)

add_executable(test_libcdaudio test_libcdaudio.c)
target_link_libraries(test_libcdaudio PRIVATE cdaudio::cdaudio)

enable_testing()
add_test(NAME test_libcdaudio COMMAND test_libcdaudio)
