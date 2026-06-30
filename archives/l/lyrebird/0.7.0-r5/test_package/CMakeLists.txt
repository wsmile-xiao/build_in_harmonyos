cmake_minimum_required(VERSION 3.15)
project(test_lyrebird C)

# Find the package via Conan-generated CMakeDeps
find_package(lyrebird REQUIRED)

add_executable(test_lyrebird test.c)
target_link_libraries(test_lyrebird lyrebird::lyrebird)

enable_testing()
add_test(NAME test_lyrebird COMMAND test_lyrebird)
