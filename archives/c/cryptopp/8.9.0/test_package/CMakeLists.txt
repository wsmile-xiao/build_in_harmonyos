cmake_minimum_required(VERSION 3.15)
project(test_cryptopp CXX)

set(CMAKE_CXX_STANDARD 17)

# Find the package via Conan-generated CMakeDeps
find_package(cryptopp REQUIRED)

add_executable(test_cryptopp test.cpp)
target_link_libraries(test_cryptopp cryptopp::cryptopp)

enable_testing()
add_test(NAME test_cryptopp COMMAND test_cryptopp)
