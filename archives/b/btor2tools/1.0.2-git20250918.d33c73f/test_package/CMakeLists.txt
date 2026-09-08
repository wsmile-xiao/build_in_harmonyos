cmake_minimum_required(VERSION 3.15)
project(test_btor2tools C)

# Find the package via Conan-generated CMakeDeps
find_package(btor2tools REQUIRED)

add_executable(test_btor2tools test.c)
target_link_libraries(test_btor2tools btor2tools::btor2tools)

enable_testing()
add_test(NAME test_btor2tools COMMAND test_btor2tools)
