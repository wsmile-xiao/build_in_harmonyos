cmake_minimum_required(VERSION 3.15)
project(test_graphite2 C CXX)

# Find the package via Conan-generated CMakeDeps
find_package(graphite2 REQUIRED)

add_executable(test_graphite2 test.cpp)
target_link_libraries(test_graphite2 graphite2::graphite2)

enable_testing()
add_test(NAME test_graphite2 COMMAND test_graphite2)
