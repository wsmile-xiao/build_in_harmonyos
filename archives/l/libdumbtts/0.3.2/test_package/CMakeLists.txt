cmake_minimum_required(VERSION 3.15)
project(test_libdumbtts C)

# Find the package via Conan-generated CMakeDeps
find_package(libdumbtts REQUIRED)

add_executable(test_libdumbtts test.c)
target_link_libraries(test_libdumbtts libdumbtts::libdumbtts)