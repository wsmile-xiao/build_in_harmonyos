cmake_minimum_required(VERSION 3.15)
project(test_liblaxjson C)

# Find the package via Conan-generated CMakeDeps
find_package(liblaxjson REQUIRED)

add_executable(test_liblaxjson test.c)
target_link_libraries(test_liblaxjson liblaxjson::liblaxjson)

enable_testing()
add_test(NAME test_liblaxjson COMMAND test_liblaxjson)
