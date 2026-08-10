cmake_minimum_required(VERSION 3.15)
project(test_odbccpp CXX)

# Find the package via Conan-generated CMakeDeps
find_package(odbccpp REQUIRED)

add_executable(test_odbccpp test.cpp)
target_link_libraries(test_odbccpp odbccpp::odbccpp)

enable_testing()
add_test(NAME test_odbccpp COMMAND test_odbccpp)
