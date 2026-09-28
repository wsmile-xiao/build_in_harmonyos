cmake_minimum_required(VERSION 3.15)
project(test_gnutrition C)

# Find the package via Conan-generated CMakeDeps
find_package(gnutrition REQUIRED)

add_executable(test_gnutrition test.c)
target_link_libraries(test_gnutrition gnutrition::gnutrition)

add_executable(harmonyos_specific_test harmonyos_specific_test.c)

enable_testing()
add_test(NAME test_gnutrition COMMAND test_gnutrition)
add_test(NAME harmonyos_specific_test COMMAND harmonyos_specific_test)
