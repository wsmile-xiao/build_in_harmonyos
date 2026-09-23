cmake_minimum_required(VERSION 3.15)
project(test_udns C)

# Find the library via Conan-generated CMakeDeps
find_package(udns CONFIG REQUIRED)

add_executable(test_udns test.c)
target_link_libraries(test_udns udns::udns)
