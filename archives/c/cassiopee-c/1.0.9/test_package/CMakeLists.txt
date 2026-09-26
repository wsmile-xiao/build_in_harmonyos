cmake_minimum_required(VERSION 3.15)
project(test_cassiopee-c CXX)

# Find the package via Conan-generated CMakeDeps
find_package(cassiopee-c REQUIRED)

add_executable(test_cassiopee-c consumer_test.cxx)
target_link_libraries(test_cassiopee-c cassiopee-c::cassie)

enable_testing()
add_test(NAME test_cassiopee-c COMMAND test_cassiopee-c)