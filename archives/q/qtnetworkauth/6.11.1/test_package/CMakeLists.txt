cmake_minimum_required(VERSION 3.16)
project(test_qtnetworkauth LANGUAGES CXX)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS NetworkAuth)

add_executable(test_qtnetworkauth test_qtnetworkauth.cpp)
target_compile_features(test_qtnetworkauth PRIVATE cxx_std_17)
target_link_libraries(
    test_qtnetworkauth
    PRIVATE Qt6::NetworkAuth
)
