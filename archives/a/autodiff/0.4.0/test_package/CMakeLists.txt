cmake_minimum_required(VERSION 3.5)
project(autodiff_test LANGUAGES CXX)
find_package(autodiff REQUIRED)

# Forward mode test (only includes forward.hpp)
add_executable(autodiff_forward_test test_forward.cpp)
target_link_libraries(autodiff_forward_test PRIVATE autodiff::autodiff)

# Reverse mode test (only includes reverse.hpp)
add_executable(autodiff_reverse_test test_reverse.cpp)
target_link_libraries(autodiff_reverse_test PRIVATE autodiff::autodiff)
