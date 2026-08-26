cmake_minimum_required(VERSION 3.15)
project(test_astrometry C)

# Find the package via Conan-generated CMakeDeps
find_package(astrometry.net REQUIRED)

add_executable(test_astrometry test.c)
target_link_libraries(test_astrometry astrometry.net::astrometry.net)

enable_testing()
add_test(NAME test_astrometry COMMAND test_astrometry)