cmake_minimum_required(VERSION 3.15)
project(test_marisa CXX)

# marisa headers/lib are built with C++20 (the upstream CMakeLists forces it);
# compile the consumer test with the same standard so the public headers match.
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(marisa REQUIRED)

add_executable(test_marisa test_marisa.cpp)
target_link_libraries(test_marisa marisa::marisa)
