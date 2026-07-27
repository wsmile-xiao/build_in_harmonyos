cmake_minimum_required(VERSION 3.15)
project(test_graphite2 C CXX)

# Find the package via Conan-generated CMakeDeps
find_package(graphite2 REQUIRED)

add_executable(test_graphite2 test.c)
target_link_libraries(test_graphite2 graphite2::graphite2)
# graphite2 is a C++ library, need C++ standard library for static linking
target_link_libraries(test_graphite2 c++)

enable_testing()
add_test(NAME test_graphite2 COMMAND test_graphite2)