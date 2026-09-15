cmake_minimum_required(VERSION 3.15)
project(test_thread_pool CXX)

# Find the package via Conan-generated CMakeDeps
find_package(thread-pool REQUIRED)

add_executable(test_thread_pool test_thread_pool.cpp)
target_link_libraries(test_thread_pool thread-pool::thread-pool)
set_target_properties(test_thread_pool PROPERTIES CXX_STANDARD 17)

enable_testing()
add_test(NAME test_thread_pool COMMAND test_thread_pool)
