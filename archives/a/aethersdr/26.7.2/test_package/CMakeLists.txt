cmake_minimum_required(VERSION 3.15)
project(test_aethersdr C)

# Find the package via Conan-generated CMakeDeps
find_package(aethersdr REQUIRED)

add_executable(test_aethersdr test.c)
target_link_libraries(test_aethersdr aethersdr::aethersdr)

enable_testing()
add_test(NAME test_aethersdr COMMAND test_aethersdr)
