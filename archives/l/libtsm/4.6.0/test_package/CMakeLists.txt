cmake_minimum_required(VERSION 3.15)
project(test_libtsm C)

# libtsm-config.cmake / libtsm::libtsm come from the Conan generated CMakeDeps
find_package(libtsm REQUIRED)

add_executable(test_libtsm test_libtsm.c)
target_link_libraries(test_libtsm libtsm::libtsm)
