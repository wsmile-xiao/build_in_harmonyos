cmake_minimum_required(VERSION 3.15)
project(test_cpplocate CXX)

# Find the package via Conan-generated CMakeDeps
find_package(cpplocate REQUIRED)

# Consumer verification test (calls the cpplocate API)
add_executable(test_cpplocate test_cpplocate.cpp)
target_link_libraries(test_cpplocate cpplocate::cpplocate)

# HarmonyOS-specific verification test (path location + platform conventions)
add_executable(test_cpplocate_hmos test_cpplocate_hmos.cpp)
target_link_libraries(test_cpplocate_hmos cpplocate::cpplocate)

enable_testing()
add_test(NAME test_cpplocate COMMAND test_cpplocate)
add_test(NAME test_cpplocate_hmos COMMAND test_cpplocate_hmos)