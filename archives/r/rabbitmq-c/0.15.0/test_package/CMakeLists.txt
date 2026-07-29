cmake_minimum_required(VERSION 3.15)
project(test_rabbitmq-c C)

# Find the package via Conan-generated CMakeDeps
find_package(rabbitmq-c REQUIRED)

add_executable(test_rabbitmq-c test.c)
target_link_libraries(test_rabbitmq-c rabbitmq-c::rabbitmq-c)

enable_testing()
add_test(NAME test_rabbitmq-c COMMAND test_rabbitmq-c)
