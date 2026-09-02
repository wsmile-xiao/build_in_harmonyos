cmake_minimum_required(VERSION 3.15)
project(test_ccronexpr C)

# Find the package via Conan-generated CMakeDeps
find_package(ccronexpr REQUIRED)

add_executable(test_ccronexpr test.c)
target_link_libraries(test_ccronexpr ccronexpr::ccronexpr)

enable_testing()
add_test(NAME test_ccronexpr COMMAND test_ccronexpr)
