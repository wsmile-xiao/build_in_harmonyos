cmake_minimum_required(VERSION 3.15)
project(test_etl CXX)

# Find the package via Conan-generated CMakeDeps
find_package(etl REQUIRED)

add_executable(test_etl test.cpp)
target_link_libraries(test_etl etl::etl)

enable_testing()
add_test(NAME test_etl COMMAND test_etl)
