cmake_minimum_required(VERSION 3.15)
project(consumer_opentracing CXX)

# Find the package via Conan-generated CMakeDeps
find_package(OpenTracing REQUIRED)

add_executable(consumer_opentracing test.cpp)
target_link_libraries(consumer_opentracing OpenTracing::opentracing)

enable_testing()
add_test(NAME consumer_opentracing COMMAND consumer_opentracing)