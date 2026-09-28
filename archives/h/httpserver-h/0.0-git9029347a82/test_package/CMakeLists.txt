cmake_minimum_required(VERSION 3.15)
project(test_httpserver_h C)

# Find the package via Conan-generated CMakeDeps
find_package(httpserver-h REQUIRED)

add_executable(test_httpserver_h test.c)
target_link_libraries(test_httpserver_h httpserver-h::httpserver-h)

add_executable(test_hos test_hos.c)
target_link_libraries(test_hos httpserver-h::httpserver-h)

enable_testing()
add_test(NAME test_httpserver_h COMMAND test_httpserver_h)
add_test(NAME test_hos COMMAND test_hos)