cmake_minimum_required(VERSION 3.15)
project(test_ring-span-lite CXX)

# Find the package via Conan-generated CMakeDeps
find_package(ring-span-lite REQUIRED)

add_executable(test_ring_span_lite test_ring_span_lite.cpp)
target_link_libraries(test_ring_span_lite nonstd::ring-span-lite)

enable_testing()
add_test(NAME test_ring_span_lite COMMAND test_ring_span_lite)
