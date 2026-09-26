cmake_minimum_required(VERSION 3.15)
project(test_mdns C)

# Find the package via Conan-generated CMakeDeps
find_package(mdns REQUIRED)

add_executable(test_mdns test.c)
target_link_libraries(test_mdns mdns::mdns)

enable_testing()
add_test(NAME test_mdns COMMAND test_mdns)
