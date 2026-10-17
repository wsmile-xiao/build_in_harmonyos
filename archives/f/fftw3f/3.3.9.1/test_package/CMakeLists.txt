cmake_minimum_required(VERSION 3.15)
project(test_fftw3f C)

find_package(FFTW3f REQUIRED)

add_executable(test_fftw3f test.c)
target_link_libraries(test_fftw3f FFTW3::fftw3f)

enable_testing()
add_test(NAME test_fftw3f COMMAND test_fftw3f)
