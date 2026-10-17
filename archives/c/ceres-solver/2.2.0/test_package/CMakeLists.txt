cmake_minimum_required(VERSION 3.15)
project(test_ceres_solver CXX)

# Find both ceres-solver and Eigen3 (ceres headers include Eigen)
find_package(ceres-solver REQUIRED)
find_package(Eigen3 REQUIRED)

add_executable(test_ceres_solver test.cpp)
target_link_libraries(test_ceres_solver ceres-solver::ceres-solver Eigen3::Eigen)

enable_testing()
add_test(NAME test_ceres_solver COMMAND test_ceres_solver)
