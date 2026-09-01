cmake_minimum_required(VERSION 3.16)
project(test_package LANGUAGES CXX)

# grpc and protobuf ship cmake_find_mode=none, so CMakeDeps does not
# generate configs for them. The generated etcd-cpp-apiv3-config.cmake
# find_dependency()s the lowercase names "grpc"/"protobuf" and its targets
# link the CMakeDeps default target names grpc::grpc / protobuf::protobuf,
# which the registry configs do not define (they define gRPC::* and
# protobuf::*). Locate the real configs first (gRPC_DIR / Protobuf_DIR are
# pinned in the test conanfile), bridge the expected target names, and
# pre-set the *_FOUND variables so the dependency loop in the generated
# config skips its (unresolvable) find_dependency calls.
find_package(gRPC CONFIG REQUIRED)
find_package(Protobuf CONFIG REQUIRED)

if(NOT TARGET grpc::grpc)
  add_library(grpc::grpc INTERFACE IMPORTED)
  # gRPC::grpc++ chains gRPC::grpc -> gpr / re2 / c-ares / openssl / absl.
  set_target_properties(grpc::grpc PROPERTIES
                        INTERFACE_LINK_LIBRARIES "gRPC::grpc++;gRPC::grpc;gRPC::gpr")
endif()
if(NOT TARGET protobuf::protobuf)
  add_library(protobuf::protobuf INTERFACE IMPORTED)
  set_target_properties(protobuf::protobuf PROPERTIES
                        INTERFACE_LINK_LIBRARIES protobuf::libprotobuf)
endif()
set(grpc_FOUND TRUE)
set(protobuf_FOUND TRUE)

find_package(etcd-cpp-apiv3 CONFIG REQUIRED)

add_executable(test_etcd test_etcd.cpp)
target_link_libraries(test_etcd PRIVATE etcd-cpp-apiv3::etcd-cpp-apiv3)

# libgrpc.a references zlib symbols but gRPC's installed config does not
# propagate zlib; link it explicitly (same as the grpc package's own test).
find_package(zlib CONFIG REQUIRED)
target_link_libraries(test_etcd PRIVATE zlib::zlib)

include(CTest)
if(BUILD_TESTING)
  add_test(NAME test_etcd COMMAND test_etcd)
endif()
