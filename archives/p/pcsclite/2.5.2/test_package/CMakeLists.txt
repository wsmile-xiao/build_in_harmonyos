cmake_minimum_required(VERSION 3.15)
project(test_pcsc C)

# Find the package via Conan-generated CMakeDeps
find_package(pcsclite REQUIRED)

add_executable(test_pcsc test.c)
target_link_libraries(test_pcsc pcsclite::pcsclite)
