# test_package/CMakeLists.txt — epoxy 1.5.10 Conan L1 test
cmake_minimum_required(VERSION 3.15)
project(test_epoxy C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Find the epoxy package via Conan-generated CMakeDeps.
find_package(epoxy REQUIRED)

add_executable(test_epoxy test.c)
target_link_libraries(test_epoxy epoxy::epoxy)
