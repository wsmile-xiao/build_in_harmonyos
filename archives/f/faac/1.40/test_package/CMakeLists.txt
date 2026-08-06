cmake_minimum_required(VERSION 3.15)
project(test_faac C)

# Find the package via Conan-generated CMakeDeps
find_package(faac REQUIRED)

add_executable(test_faac test.c)
target_link_libraries(test_faac faac::faac)

enable_testing()
add_test(NAME test_faac COMMAND test_faac)
