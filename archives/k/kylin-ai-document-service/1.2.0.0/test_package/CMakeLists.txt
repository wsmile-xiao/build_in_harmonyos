cmake_minimum_required(VERSION 3.16)
project(test_package LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# grpc and protobuf ship cmake_find_mode=none, so CMakeDeps does not generate
# configs for them. Locate the real registry configs first (the *_DIR
# variables are pinned by the test conanfile), bridge the lowercase target
# names the generated config expects, and pre-set the *_FOUND variables so the
# dependency loop in the generated config skips its find_dependency calls.
find_package(gRPC CONFIG REQUIRED)
find_package(Protobuf CONFIG REQUIRED)

if(NOT TARGET grpc::grpc)
  add_library(grpc::grpc INTERFACE IMPORTED)
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

find_package(kylin-ai-document-service CONFIG REQUIRED)

add_executable(test_document_service test_document_service.cpp)
target_link_libraries(test_document_service PRIVATE
                      kylin-ai-document-service::kylin-ai-document-service)
