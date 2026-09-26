cmake_minimum_required(VERSION 3.15)
project(test_genders C)

# Find the package via Conan-generated CMakeDeps
find_package(genders REQUIRED)

add_executable(test_genders test.c)
target_link_libraries(test_genders genders::genders)
