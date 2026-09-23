cmake_minimum_required(VERSION 3.15)
project(test_rtrlib C)

# The packaged librtr is found via Conan-generated CMakeDeps files.
find_package(rtrlib REQUIRED)

add_executable(test_pfx_validation test_pfx_validation.c)
target_link_libraries(test_pfx_validation PRIVATE rtrlib::rtrlib)

add_executable(test_version_utils test_version_utils.c)
target_link_libraries(test_version_utils PRIVATE rtrlib::rtrlib)

enable_testing()
add_test(NAME test_pfx_validation COMMAND test_pfx_validation)
add_test(NAME test_version_utils COMMAND test_version_utils)
