cmake_minimum_required(VERSION 3.15)
project(test_semver CXX)

# Find the package via Conan-generated CMakeDeps
find_package(semver REQUIRED)

add_executable(test_semver test_package.cpp)
target_link_libraries(test_semver semver::semver)

enable_testing()
add_test(NAME test_semver COMMAND test_semver)