cmake_minimum_required(VERSION 3.15)
project(leopard_test_package LANGUAGES CXX)

find_package(ThreadPool CONFIG REQUIRED)

add_executable(test_leopard test_leopard.cpp)
# Leopard's headers are C++20 (concepts / std::optional); pin it explicitly so
# the consumer never inherits the CI profile's compiler.cppstd=17.
set_target_properties(test_leopard PROPERTIES
    CXX_STANDARD 20
    CXX_STANDARD_REQUIRED ON
)
target_link_libraries(test_leopard PRIVATE ThreadPool::ThreadPool)

enable_testing()
add_test(NAME test_leopard COMMAND test_leopard)
