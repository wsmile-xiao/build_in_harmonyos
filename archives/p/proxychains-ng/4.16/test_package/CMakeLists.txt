cmake_minimum_required(VERSION 3.15)
project(test_proxychains_ng C)

# Find the package via Conan-generated CMakeDeps
find_package(proxychains-ng REQUIRED)

add_executable(test_proxychains_ng test.c)
target_link_libraries(test_proxychains_ng proxychains-ng::proxychains-ng)

enable_testing()
add_test(NAME test_proxychains_ng COMMAND test_proxychains_ng)
