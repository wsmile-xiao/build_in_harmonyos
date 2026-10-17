cmake_minimum_required(VERSION 3.15)
project(test_fftw C)

find_package(fftw REQUIRED)

add_executable(test_fftw test.c)
target_link_libraries(test_fftw fftw::fftw)

enable_testing()
add_test(NAME test_fftw COMMAND test_fftw)
