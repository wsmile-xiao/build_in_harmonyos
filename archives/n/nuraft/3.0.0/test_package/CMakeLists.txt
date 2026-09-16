cmake_minimum_required(VERSION 3.15)
project(test_nuraft CXX)

# Find the package via Conan-generated CMakeDeps
find_package(nuraft REQUIRED)

add_executable(test_nuraft test_nuraft.cpp in_memory_log_store.cxx)
target_link_libraries(test_nuraft nuraft::nuraft)

enable_testing()
add_test(NAME test_nuraft COMMAND test_nuraft)