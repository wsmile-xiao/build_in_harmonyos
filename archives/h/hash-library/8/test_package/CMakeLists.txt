cmake_minimum_required(VERSION 3.15)
project(test_hash-library CXX)

# Find the package via Conan-generated CMakeDeps
find_package(hash-library REQUIRED)

add_executable(test_hash-library test_consumer.cpp)
target_link_libraries(test_hash-library hash-library::hash-library)

enable_testing()
add_test(NAME test_hash-library COMMAND test_hash-library)
