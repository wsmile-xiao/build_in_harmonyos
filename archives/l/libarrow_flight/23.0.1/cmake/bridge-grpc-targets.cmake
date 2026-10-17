# Bridge targets for registry packages with cmake_find_mode=none.
#
# The registry grpc/protobuf packages ship their native CMake configs:
#   - gRPCConfig.cmake exports gRPC::grpc++ / gRPC::grpc / gRPC::gpr
#   - protobuf-config.cmake exports protobuf::libprotobuf / protobuf::protoc
# Conan component references for component-less recipes must use the literal
# "<pkgname>::<pkgname>" form, so libarrow_flight's package_info refers to
# grpc::grpc and protobuf::protobuf. This module (shipped via
# cmake_build_modules so downstream CMakeDeps consumers include it
# automatically) creates those alias names whenever the native configs have
# already been loaded. grpc::grpc points at gRPC::grpc++ because Flight is a
# C++ consumer (grpc++ pulls in grpc + gpr transitively).
if(NOT TARGET grpc::grpc)
    if(TARGET gRPC::grpc++)
        add_library(grpc::grpc INTERFACE IMPORTED)
        set_target_properties(grpc::grpc PROPERTIES
                              INTERFACE_LINK_LIBRARIES gRPC::grpc++)
    endif()
endif()
if(NOT TARGET protobuf::protobuf)
    if(TARGET protobuf::libprotobuf)
        add_library(protobuf::protobuf INTERFACE IMPORTED)
        set_target_properties(protobuf::protobuf PROPERTIES
                              INTERFACE_LINK_LIBRARIES protobuf::libprotobuf)
    endif()
endif()
