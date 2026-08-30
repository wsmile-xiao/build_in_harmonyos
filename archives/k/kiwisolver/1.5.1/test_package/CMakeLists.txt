cmake_minimum_required(VERSION 3.15)
project(test_kiwisolver LANGUAGES CXX)

find_package(kiwisolver CONFIG REQUIRED)

add_executable(test_kiwisolver test_kiwisolver.cpp)
target_link_libraries(test_kiwisolver PRIVATE kiwisolver::kiwisolver)

enable_testing()
add_test(NAME test_kiwisolver COMMAND test_kiwisolver)
