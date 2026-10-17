cmake_minimum_required(VERSION 3.15)
project(test_psimd LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(psimd REQUIRED)

add_executable(test_psimd test.cc)
target_link_libraries(test_psimd PRIVATE psimd::psimd)

enable_testing()
add_test(NAME test_psimd COMMAND test_psimd)
