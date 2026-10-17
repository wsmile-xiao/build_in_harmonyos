cmake_minimum_required(VERSION 3.15)
project(test_bulletml CXX)

# Find the package via Conan-generated CMakeDeps
find_package(bulletml REQUIRED)

add_executable(test_bulletml test.cpp)
target_link_libraries(test_bulletml bulletml::bulletml)

enable_testing()
add_test(NAME test_bulletml COMMAND test_bulletml)
