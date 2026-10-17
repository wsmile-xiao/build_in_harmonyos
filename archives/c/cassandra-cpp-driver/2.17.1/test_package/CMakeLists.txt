cmake_minimum_required(VERSION 3.15)
project(test_cassandra_cpp_driver C CXX)

# Find the package via Conan-generated CMakeDeps
find_package(cassandra-cpp-driver REQUIRED)

add_executable(test_cassandra_cpp_driver test.c)
target_link_libraries(test_cassandra_cpp_driver cassandra-cpp-driver::cassandra)

enable_testing()
add_test(NAME test_cassandra_cpp_driver COMMAND test_cassandra_cpp_driver)
