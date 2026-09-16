cmake_minimum_required(VERSION 3.15)
project(test_ccrtp CXX)

# Find the package via Conan-generated CMakeDeps
find_package(ccrtp REQUIRED)

add_executable(test_ccrtp test_ccrtp.cpp)
target_link_libraries(test_ccrtp ccrtp::ccrtp)
set_target_properties(test_ccrtp PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
)

enable_testing()
add_test(NAME test_ccrtp COMMAND test_ccrtp)
