cmake_minimum_required(VERSION 3.16)
project(test_package LANGUAGES CXX)

find_package(gRPC CONFIG REQUIRED)
find_package(Protobuf CONFIG REQUIRED)
# libgrpc.a references zlib symbols (message_compress) but grpc's installed
# config does not propagate zlib, so link it explicitly via CMakeDeps target.
find_package(zlib CONFIG REQUIRED)

add_executable(test_grpc test_grpc.cpp)
target_link_libraries(test_grpc PRIVATE gRPC::grpc++ zlib::zlib)

include(CTest)
if(BUILD_TESTING)
  add_test(NAME test_grpc COMMAND test_grpc)
endif()
