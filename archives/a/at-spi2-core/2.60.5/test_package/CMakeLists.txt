cmake_minimum_required(VERSION 3.15)
project(test_atk C)

# Find at-spi2-core via Conan-generated CMakeDeps (component targets).
find_package(at-spi2-core REQUIRED)

add_executable(test_atk test_atk.c)
target_link_libraries(test_atk at-spi2-core::atk at-spi2-core::atspi)

enable_testing()
add_test(NAME test_atk COMMAND test_atk)
