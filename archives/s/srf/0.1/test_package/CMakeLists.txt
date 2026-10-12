cmake_minimum_required(VERSION 3.15)
project(test_srf CXX)

# srf ships no CMake config; CMakeDeps generates one (find_package name
# = recipe name, target srf::srf).
find_package(srf REQUIRED CONFIG)
find_package(io_lib REQUIRED CONFIG)

add_executable(test_srf_ztr test_srf_ztr.cc)
target_link_libraries(test_srf_ztr srf::srf io_lib::io_lib)

enable_testing()
add_test(NAME srf_ztr_roundtrip COMMAND test_srf_ztr)
