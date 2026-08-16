cmake_minimum_required(VERSION 3.15)
project(test_ice CXX)

# Find the package via Conan-generated CMakeDeps
find_package(ice REQUIRED)

add_executable(test_ice test.cpp)
target_link_libraries(test_ice ice::ice)

enable_testing()
add_test(NAME test_ice COMMAND test_ice)
