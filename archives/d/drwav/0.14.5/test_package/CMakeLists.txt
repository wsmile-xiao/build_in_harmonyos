cmake_minimum_required(VERSION 3.15)
project(test_drwav C)

# Find the package via Conan-generated CMakeDeps
find_package(drwav REQUIRED)

add_executable(test_drwav test.c)
target_link_libraries(test_drwav drwav::drwav)

enable_testing()
add_test(NAME test_drwav COMMAND test_drwav)
