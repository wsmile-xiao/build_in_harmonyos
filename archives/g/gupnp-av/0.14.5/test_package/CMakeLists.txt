cmake_minimum_required(VERSION 3.15)
project(test_gupnp_av C)

# Find the package via Conan-generated CMakeDeps.
find_package(gupnp-av-1.0 REQUIRED)

add_executable(test_gupnp_av test_gupnp_av.c)
target_link_libraries(test_gupnp_av gupnp-av-1.0::gupnp-av-1.0)

enable_testing()
add_test(NAME test_gupnp_av COMMAND test_gupnp_av)
