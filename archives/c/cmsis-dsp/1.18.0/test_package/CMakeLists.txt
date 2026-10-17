cmake_minimum_required(VERSION 3.15)
project(test_cmsis-dsp C)

# Find the package via Conan-generated CMakeDeps (cmake_file_name=CMSISDSP)
find_package(CMSISDSP REQUIRED)

add_executable(test_cmsis-dsp test.c)
target_link_libraries(test_cmsis-dsp CMSISDSP::CMSISDSP)

enable_testing()
add_test(NAME test_cmsis-dsp COMMAND test_cmsis-dsp)
