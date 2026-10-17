cmake_minimum_required(VERSION 3.16)
project(test_package LANGUAGES C CXX)

# libgrpc_authorization_provider ships no CMake config (module split,
# cmake_find_mode=none). Link the static archives directly, in dependency
# order. abseil/re2/openssl/c-ares/zlib come through CMakeDeps targets.
# The consumer API is the C core (grpc/grpc_security.h): the upstream C++
# binding TU (src/cpp/server/authorization_policy_provider.cc) is compiled
# by upstream only into its own test binaries, so no protobuf linkage is
# needed here.
find_package(abseil-cpp REQUIRED)
find_package(re2 REQUIRED)
find_package(openssl REQUIRED)
find_package(c-ares REQUIRED)
find_package(zlib REQUIRED)

set(GRPC_LIBS
  ${LIBGRPC_AUTH_LIB_DIR}/libgrpc_authorization_provider.a
  ${LIBGRPC_AUTH_LIB_DIR}/libgpr.a
  ${LIBGRPC_AUTH_LIB_DIR}/libupb_textformat_lib.a
  ${LIBGRPC_AUTH_LIB_DIR}/libupb_reflection_lib.a
  ${LIBGRPC_AUTH_LIB_DIR}/libupb_mini_descriptor_lib.a
  ${LIBGRPC_AUTH_LIB_DIR}/libupb_mini_table_lib.a
  ${LIBGRPC_AUTH_LIB_DIR}/libupb_message_lib.a
  ${LIBGRPC_AUTH_LIB_DIR}/libupb_wire_lib.a
  ${LIBGRPC_AUTH_LIB_DIR}/libupb_json_lib.a
  ${LIBGRPC_AUTH_LIB_DIR}/libupb_lex_lib.a
  ${LIBGRPC_AUTH_LIB_DIR}/libupb_hash_lib.a
  ${LIBGRPC_AUTH_LIB_DIR}/libupb_mem_lib.a
  ${LIBGRPC_AUTH_LIB_DIR}/libupb_descriptor_lib.a
  ${LIBGRPC_AUTH_LIB_DIR}/libupb_base_lib.a
  ${LIBGRPC_AUTH_LIB_DIR}/libutf8_range_lib.a
  ${LIBGRPC_AUTH_LIB_DIR}/libaddress_sorting.a
)

add_executable(test_package test_package.cpp)
target_include_directories(test_package PRIVATE ${LIBGRPC_AUTH_INC_DIR})
target_link_libraries(test_package PRIVATE
  ${GRPC_LIBS}
  abseil-cpp::abseil-cpp
  re2::re2
  openssl::openssl
  c-ares::c-ares
  zlib::zlib
)

include(CTest)
if(BUILD_TESTING)
  add_test(NAME test_package COMMAND test_package)
endif()
