# Minimal CMake build for the protoc-gen-grpc-web plugin.
#
# Upstream grpc-web builds its protoc plugin with Bazel (see
# javascript/net/grpc/web/generator/BUILD.bazel). Bazel is not part of
# the HarmonyOS PC toolchain matrix, so this recipe reuses the upstream
# plugin source file verbatim (after the protobuf 33 compatibility patch)
# and links it against the Conan-provided protobuf::libprotoc imported
# target, which transitively resolves libprotobuf, libutf8_validity,
# libutf8_range and every required absl::* library.
cmake_minimum_required(VERSION 3.16)
project(protoc-gen-grpc-web LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Protobuf CONFIG REQUIRED)

add_executable(protoc-gen-grpc-web
  javascript/net/grpc/web/generator/grpc_generator.cc)
target_link_libraries(protoc-gen-grpc-web PRIVATE protobuf::libprotoc)

include(GNUInstallDirs)
install(TARGETS protoc-gen-grpc-web RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
