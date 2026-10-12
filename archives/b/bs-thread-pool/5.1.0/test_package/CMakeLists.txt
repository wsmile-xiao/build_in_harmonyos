cmake_minimum_required(VERSION 3.15)
project(test_bs_thread_pool CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(bs-thread-pool REQUIRED)

add_executable(test_bs_thread_pool test_bs_thread_pool.cpp)
target_link_libraries(test_bs_thread_pool bs-thread-pool::bs-thread-pool)

enable_testing()
add_test(NAME test_bs_thread_pool COMMAND test_bs_thread_pool)
