cmake_minimum_required(VERSION 3.15)
project(test_rdma_core C)

# Find the package via Conan-generated CMakeDeps
find_package(rdma-core REQUIRED)

add_executable(test_rdma_core test.c)
target_link_libraries(test_rdma_core rdma-core::rdma-core)

enable_testing()
add_test(NAME test_rdma_core COMMAND test_rdma_core)
