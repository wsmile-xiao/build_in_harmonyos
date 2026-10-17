cmake_minimum_required(VERSION 3.15)
project(test_wavpack C)

find_package(WavPack REQUIRED)

add_executable(test_wavpack test_wavpack.c)
target_link_libraries(test_wavpack WavPack::WavPack)

enable_testing()
add_test(NAME test_wavpack COMMAND test_wavpack)
