cmake_minimum_required(VERSION 3.16)
project(test_highway CXX)

find_package(hwy REQUIRED CONFIG)

add_executable(test_highway src/test_highway.cc)
target_link_libraries(test_highway PRIVATE hwy::hwy)

set_target_properties(test_highway PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
)

enable_testing()
add_test(NAME highway_simd_test COMMAND test_highway)
