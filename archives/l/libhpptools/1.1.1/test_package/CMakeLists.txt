cmake_minimum_required(VERSION 3.10)
project(test_package CXX)

include(${CMAKE_BINARY_DIR}/generators/conan_toolchain.cmake)

find_package(hpptools REQUIRED CONFIG)
find_package(Boost REQUIRED CONFIG)

# The upstream Catch suite and the library itself are C++11 (catch.hpp v1.x
# uses std::random_shuffle, removed in C++17; the profile default is 17).
# Pin the test_package targets to the library's own C++11 contract.
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(test_consumer test_consumer.cpp)
target_link_libraries(test_consumer PRIVATE hpptools::hpptools)

# The unmodified upstream Catch suite (examples/test-alg.cpp + bundled
# catch.hpp from hpptools-1.1.1), compiled against the packaged headers.
add_executable(test_alg test_alg.cpp)
target_link_libraries(test_alg PRIVATE hpptools::hpptools boost::boost)

enable_testing()
add_test(NAME consumer_smoke COMMAND test_consumer)
add_test(NAME upstream_catch_suite COMMAND test_alg)
