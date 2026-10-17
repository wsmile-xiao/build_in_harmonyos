cmake_minimum_required(VERSION 3.15)
project(test_ipaddress CXX)

# Find the package via Conan-generated CMakeDeps
find_package(ipaddress REQUIRED)

add_executable(test_ipaddress test.cpp)
target_link_libraries(test_ipaddress ipaddress::ipaddress)
target_compile_features(test_ipaddress PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_ipaddress COMMAND test_ipaddress)
