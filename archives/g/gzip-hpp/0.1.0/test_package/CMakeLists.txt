cmake_minimum_required(VERSION 3.15)
project(test_gzip_hpp CXX)

# Find the package via Conan-generated CMakeDeps
find_package(gzip-hpp REQUIRED)

add_executable(test_gzip_hpp test_gzip_hpp.cpp)
target_link_libraries(test_gzip_hpp gzip-hpp::gzip-hpp)
set_target_properties(test_gzip_hpp PROPERTIES CXX_STANDARD 11)

enable_testing()
add_test(NAME test_gzip_hpp COMMAND test_gzip_hpp)
