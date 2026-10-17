cmake_minimum_required(VERSION 3.15)
project(test_gupnp_tools C)

# gupnp-tools is an application package (binaries only, no libraries and no
# public headers). The L1 test therefore does not link against it: the real
# verification happens in conanfile.py test(), which executes the packaged
# binaries (gssdp-discover --help / gssdp-discover -n 1 / bounded
# gupnp-event-dumper run). This minimal CMake project just drives the conan
# test_package build layout.
message(STATUS "gupnp-tools test_package: application package — binaries executed in test()")

add_executable(test_gupnp_tools test_gupnp_tools.c)

enable_testing()
add_test(NAME test_gupnp_tools COMMAND test_gupnp_tools)
