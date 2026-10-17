cmake_minimum_required(VERSION 3.22)
project(test_package LANGUAGES CXX)

# grpc 1.84.0 requires C++17 (per-target cxx_std_17 features upstream).
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(gRPC CONFIG REQUIRED)
find_package(Protobuf CONFIG REQUIRED)
# libgrpc.a references zlib symbols (message_compress) but grpc's installed
# config does not propagate zlib, so link it explicitly via the CMakeDeps
# target.
find_package(zlib CONFIG REQUIRED)

add_executable(test_grpc test_grpc.cpp)
target_link_libraries(test_grpc PRIVATE gRPC::grpc++ zlib::zlib)

enable_testing()
add_test(NAME test_grpc COMMAND test_grpc)
