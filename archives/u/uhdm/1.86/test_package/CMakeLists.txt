cmake_minimum_required(VERSION 3.15)
project(test_uhdm CXX)

# Find the package via Conan-generated CMakeDeps
find_package(uhdm REQUIRED)

add_executable(test_uhdm test.cpp)
target_link_libraries(test_uhdm PRIVATE uhdm::uhdm)

enable_testing()
add_test(NAME test_uhdm COMMAND test_uhdm)
