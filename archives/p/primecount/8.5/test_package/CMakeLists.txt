cmake_minimum_required(VERSION 3.15)
project(test_primecount CXX)

# Find the package via Conan-generated CMakeDeps.
find_package(primecount REQUIRED)

add_executable(test_primecount test.cpp)
target_link_libraries(test_primecount primecount::primecount)

enable_testing()
add_test(NAME test_primecount COMMAND test_primecount)
