cmake_minimum_required(VERSION 3.15)
project(test_eabase CXX)

# Find the package via Conan-generated CMakeDeps
find_package(eabase REQUIRED)

add_executable(test_eabase test.cpp)
target_link_libraries(test_eabase eabase::eabase)

enable_testing()
add_test(NAME test_eabase COMMAND test_eabase)