cmake_minimum_required(VERSION 3.15)
project(test_tsduck_consumer CXX)

# Upstream requires C++20 (src/libtscore uses concept/requires/
# std::integral in tsIntegerUtils.h); the repo profile pins cppstd=17,
# so enforce 20 here regardless of the toolchain default.
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(tsduck REQUIRED)

add_executable(test_tsduck test_tsduck.cpp)
target_compile_features(test_tsduck PRIVATE cxx_std_20)
target_link_libraries(test_tsduck PRIVATE tsduck::tsduck)
