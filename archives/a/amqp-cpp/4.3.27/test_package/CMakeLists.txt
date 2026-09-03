cmake_minimum_required(VERSION 3.15)
project(test_amqp-cpp CXX)

# Find the package via Conan-generated CMakeDeps
find_package(amqp-cpp REQUIRED)

add_executable(test_amqp-cpp test.cpp)
target_link_libraries(test_amqp-cpp amqp-cpp::amqp-cpp)

enable_testing()
add_test(NAME test_amqp-cpp COMMAND test_amqp-cpp)
