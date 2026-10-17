cmake_minimum_required(VERSION 3.5)
project(test_ifopt CXX)

find_package(ifopt CONFIG REQUIRED)
find_package(Eigen3 CONFIG REQUIRED)

add_executable(test_ifopt test_ifopt.cpp)
target_link_libraries(test_ifopt PRIVATE ifopt::ifopt_core Eigen3::Eigen)
target_compile_features(test_ifopt PRIVATE cxx_std_17)
