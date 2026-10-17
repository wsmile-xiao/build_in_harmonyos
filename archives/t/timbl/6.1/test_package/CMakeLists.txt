cmake_minimum_required(VERSION 3.15)
project(test_timbl CXX)

set(CMAKE_CXX_STANDARD 17)

# Find the package via Conan-generated CMakeDeps
find_package(timbl REQUIRED)

add_executable(test_timbl test.cxx)
target_link_libraries(test_timbl timbl::timbl)

enable_testing()
add_test(NAME test_timbl COMMAND test_timbl)
