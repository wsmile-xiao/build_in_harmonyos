cmake_minimum_required(VERSION 3.15)
project(test_vineyard CXX)

# Find the package via Conan-generated CMakeDeps (vineyard-config.cmake).
find_package(vineyard CONFIG REQUIRED)

add_executable(test_vineyard test_package.cpp)
target_link_libraries(test_vineyard PRIVATE vineyard::vineyard_client)

enable_testing()
add_test(NAME test_vineyard COMMAND test_vineyard)
