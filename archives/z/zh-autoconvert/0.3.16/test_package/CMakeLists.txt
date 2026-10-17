cmake_minimum_required(VERSION 3.15)
project(autoconvert_test C)

# Located via Conan-generated CMakeDeps (zh-autoconvertConfig.cmake).
find_package(zh-autoconvert REQUIRED)

add_executable(test_hz test.c)
target_link_libraries(test_hz PRIVATE zh-autoconvert::zh-autoconvert)

enable_testing()
add_test(NAME test_hz COMMAND test_hz)
