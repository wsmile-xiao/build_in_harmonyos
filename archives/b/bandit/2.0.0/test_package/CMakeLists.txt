cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(bandit REQUIRED CONFIG)

add_executable(test_bandit test_bandit.cpp)
target_link_libraries(test_bandit PRIVATE bandit::bandit)
target_compile_features(test_bandit PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_bandit COMMAND test_bandit --no-color --reporter=dots)
