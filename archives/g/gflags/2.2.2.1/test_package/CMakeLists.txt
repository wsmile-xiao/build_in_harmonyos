cmake_minimum_required(VERSION 3.16)
project(test_gflags LANGUAGES CXX)

set(GFLAGS_USE_TARGET_NAMESPACE TRUE)
find_package(gflags CONFIG REQUIRED)

add_executable(test_gflags test_gflags.cpp)
target_compile_features(test_gflags PRIVATE cxx_std_11)
target_link_libraries(test_gflags PRIVATE gflags::gflags)
