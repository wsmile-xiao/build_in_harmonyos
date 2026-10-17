cmake_minimum_required(VERSION 3.15)
project(test_libcuckoo_acp CXX)

set(CMAKE_CXX_STANDARD 11)

# Find the package via Conan-generated CMakeDeps
find_package(libcuckoo REQUIRED)

add_executable(test_libcuckoo_acp test_libcuckoo_acp.cpp)
target_link_libraries(test_libcuckoo_acp libcuckoo::libcuckoo)

enable_testing()
add_test(NAME test_libcuckoo_acp COMMAND test_libcuckoo_acp)
