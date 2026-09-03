cmake_minimum_required(VERSION 3.15)
project(test_librdkafka C)

# Find the package via Conan-generated CMakeDeps
find_package(librdkafka REQUIRED)

add_executable(test_librdkafka test.c)
target_link_libraries(test_librdkafka librdkafka::librdkafka)

enable_testing()
add_test(NAME test_librdkafka COMMAND test_librdkafka)
