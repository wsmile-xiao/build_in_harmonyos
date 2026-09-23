cmake_minimum_required(VERSION 3.15)
project(test_opencl_clhpp_headers CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(opencl-clhpp-headers REQUIRED)
find_package(opencl-headers REQUIRED)

# CL/opencl.hpp template destructors reference OpenCL API symbols
# (clReleaseDevice etc.) which require the ICD loader to link.
# Use --unresolved-symbols=ignore-all to allow linking without the ICD loader.
# All tests use compile-time checks (static_assert, type traits), no runtime API calls.

# Test 1: Basic include verification
add_executable(test_include test.cpp)
target_link_libraries(test_include opencl-clhpp-headers::opencl-clhpp-headers)
target_link_options(test_include PRIVATE "-Wl,--unresolved-symbols=ignore-all")

# Test 2: Version macro verification
add_executable(test_version test_version.cpp)
target_link_libraries(test_version opencl-clhpp-headers::opencl-clhpp-headers)
target_link_options(test_version PRIVATE "-Wl,--unresolved-symbols=ignore-all")

# Test 3: Core C++ type verification (Platform, Device, Context, etc.)
add_executable(test_types test_types.cpp)
target_link_libraries(test_types opencl-clhpp-headers::opencl-clhpp-headers)
target_link_options(test_types PRIVATE "-Wl,--unresolved-symbols=ignore-all")

# Test 4: API surface verification (enums, flags, string type)
add_executable(test_api_surface test_api_surface.cpp)
target_link_libraries(test_api_surface opencl-clhpp-headers::opencl-clhpp-headers)
target_link_options(test_api_surface PRIVATE "-Wl,--unresolved-symbols=ignore-all")

enable_testing()
add_test(NAME test_include COMMAND test_include)
add_test(NAME test_version COMMAND test_version)
add_test(NAME test_types COMMAND test_types)
add_test(NAME test_api_surface COMMAND test_api_surface)
