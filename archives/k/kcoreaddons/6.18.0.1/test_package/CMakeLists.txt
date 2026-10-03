cmake_minimum_required(VERSION 3.15)
project(test_kcoreaddons CXX)

find_package(KF6CoreAddons REQUIRED)

add_executable(test_kcoreaddons test.cpp)
target_link_libraries(test_kcoreaddons KF6::CoreAddons)

enable_testing()
add_test(NAME test_kcoreaddons COMMAND test_kcoreaddons)
