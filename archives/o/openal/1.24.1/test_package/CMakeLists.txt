cmake_minimum_required(VERSION 3.15)
project(test_openal C CXX)

find_package(OpenAL REQUIRED CONFIG)

# Dependency-free port of the upstream tests/example.t.cpp case.
add_executable(upstream_basic upstream_basic.cpp)
target_link_libraries(upstream_basic PRIVATE OpenAL::OpenAL)

# Consumer workflow: null backend + ALC_SOFT_loopback rendering.
# The library is C++ internally, so link the C test with the C++ driver.
add_executable(test_openal_consumer test_openal.c)
set_property(TARGET test_openal_consumer PROPERTY LINKER_LANGUAGE CXX)
target_link_libraries(test_openal_consumer PRIVATE OpenAL::OpenAL m)
