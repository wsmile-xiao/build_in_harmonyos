cmake_minimum_required(VERSION 3.15)
project(test_ccfits CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(CCfits REQUIRED)

add_executable(test_ccfits test_ccfits.cpp)
target_link_libraries(test_ccfits CCfits::CCfits)

enable_testing()
add_test(NAME test_ccfits COMMAND test_ccfits)
