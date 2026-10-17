cmake_minimum_required(VERSION 3.15)
project(test_clownresampler C)

# Find the package via Conan-generated CMakeDeps
find_package(clownresampler REQUIRED)

add_executable(test_clownresampler test.c)
target_link_libraries(test_clownresampler clownresampler::clownresampler)

enable_testing()
add_test(NAME test_clownresampler COMMAND test_clownresampler)
