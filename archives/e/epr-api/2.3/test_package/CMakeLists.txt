cmake_minimum_required(VERSION 3.15)
project(test_epr-api C)

# Find the package via Conan-generated CMakeDeps
find_package(epr-api REQUIRED)

add_executable(test_epr-api test.c)
target_link_libraries(test_epr-api epr-api::epr-api)

enable_testing()
add_test(NAME test_epr-api COMMAND test_epr-api)
