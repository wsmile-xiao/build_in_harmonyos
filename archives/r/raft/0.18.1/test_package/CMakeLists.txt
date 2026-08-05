cmake_minimum_required(VERSION 3.15)
project(test_raft C)

# Find the package via Conan-generated CMakeDeps
find_package(raft REQUIRED)

add_executable(test_raft test.c)
target_link_libraries(test_raft raft::raft)

enable_testing()
add_test(NAME test_raft COMMAND test_raft)
