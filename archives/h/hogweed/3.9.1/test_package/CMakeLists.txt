cmake_minimum_required(VERSION 3.15)
project(hogweed_test LANGUAGES C CXX)

find_package(hogweed CONFIG REQUIRED)
find_package(gmp CONFIG REQUIRED)
add_executable(hogweed_test test_package.cpp)
target_link_libraries(hogweed_test PRIVATE hogweed::hogweed gmp::gmp)