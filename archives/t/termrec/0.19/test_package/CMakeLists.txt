cmake_minimum_required(VERSION 3.15)
project(test_termrec C)

# Find the package via Conan-generated CMakeDeps
find_package(termrec REQUIRED)

add_executable(test_consumer test_consumer.c)
target_link_libraries(test_consumer termrec::termrec)

enable_testing()
add_test(NAME consumer_roundtrip COMMAND test_consumer)
