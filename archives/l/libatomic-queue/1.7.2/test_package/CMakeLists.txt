cmake_minimum_required(VERSION 3.15)
project(test_atomic_queue CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(atomic_queue REQUIRED)

add_executable(test_atomic_queue test_atomic_queue.cpp)
target_link_libraries(test_atomic_queue PRIVATE atomic_queue::atomic_queue)
find_package(Threads REQUIRED)
target_link_libraries(test_atomic_queue PRIVATE Threads::Threads)

enable_testing()
add_test(NAME test_atomic_queue COMMAND test_atomic_queue)
