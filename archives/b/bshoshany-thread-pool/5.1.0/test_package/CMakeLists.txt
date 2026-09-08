cmake_minimum_required(VERSION 3.15)
project(test_bs_thread_pool CXX)

# Find the package via Conan-generated CMakeDeps
find_package(bshoshany-thread-pool REQUIRED)

add_executable(test_bs_thread_pool test_bs_thread_pool.cpp)
target_link_libraries(test_bs_thread_pool bshoshany-thread-pool::bshoshany-thread-pool)
set_target_properties(test_bs_thread_pool PROPERTIES CXX_STANDARD 17)
# Compile the consumer with the native extensions so the OHOS-patched
# affinity code path (sched_getaffinity/sched_setaffinity) is exercised.
target_compile_definitions(test_bs_thread_pool PRIVATE BS_THREAD_POOL_NATIVE_EXTENSIONS)

enable_testing()
add_test(NAME test_bs_thread_pool COMMAND test_bs_thread_pool)
