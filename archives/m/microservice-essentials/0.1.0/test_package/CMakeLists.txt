cmake_minimum_required(VERSION 3.15)
project(test_microservice_essentials CXX)

# Find the package via Conan-generated CMakeDeps
find_package(microservice-essentials REQUIRED)

add_executable(test_microservice_essentials main.cpp)
target_link_libraries(test_microservice_essentials microservice-essentials::microservice-essentials)

enable_testing()
add_test(NAME test_microservice_essentials COMMAND test_microservice_essentials)
