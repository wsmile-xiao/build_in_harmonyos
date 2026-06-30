cmake_minimum_required(VERSION 3.15)
project(test_xmrig-proxy C)

# Find the package via Conan-generated CMakeDeps
find_package(xmrig-proxy REQUIRED)

add_executable(test_xmrig-proxy test.c)
target_link_libraries(test_xmrig-proxy xmrig-proxy::xmrig-proxy)

enable_testing()
add_test(NAME test_xmrig-proxy COMMAND test_xmrig-proxy)
