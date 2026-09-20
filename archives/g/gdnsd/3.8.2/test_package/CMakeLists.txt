cmake_minimum_required(VERSION 3.15)
project(test_gdnsd C)

# Find the package via Conan-generated CMakeDeps
find_package(gdnsd REQUIRED)

add_executable(test_gdnsd test.c)

# Link against gdnsd package
target_link_libraries(test_gdnsd gdnsd::gdnsd)

enable_testing()
add_test(NAME test_gdnsd COMMAND test_gdnsd)
