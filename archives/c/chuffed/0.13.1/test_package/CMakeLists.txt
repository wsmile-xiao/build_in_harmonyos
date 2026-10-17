cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(chuffed REQUIRED CONFIG)

# Scenario 1: satisfiability (all-solutions 6-Queens)
add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE chuffed::chuffed)
target_compile_features(test_package PRIVATE cxx_std_11)

# Scenario 2: optimisation (maximise) — separate process because the
# chuffed engine singleton solves one problem per process.
add_executable(test_optimize test_optimize.cpp)
target_link_libraries(test_optimize PRIVATE chuffed::chuffed)
target_compile_features(test_optimize PRIVATE cxx_std_11)
