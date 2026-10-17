cmake_minimum_required(VERSION 3.15)
project(test_mffm-fftw CXX)

# Find the package via Conan-generated CMakeDeps
find_package(mffm-fftw REQUIRED)
# mffm-fftw 公共头文件 include <fftw3.h>，消费者须链接 fftw 以解析头文件与符号
find_package(fftw REQUIRED)

add_executable(test_mffm-fftw test_mffm_fftw.cpp)
target_link_libraries(test_mffm-fftw mffm-fftw::mffm-fftw fftw::fftw)

enable_testing()
add_test(NAME test_mffm-fftw COMMAND test_mffm-fftw)
