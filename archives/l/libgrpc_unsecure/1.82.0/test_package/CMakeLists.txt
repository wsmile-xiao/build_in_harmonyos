cmake_minimum_required(VERSION 3.16)
project(test_package LANGUAGES CXX)

# libgrpc_unsecure ships no CMake config (module split, cmake_find_mode=none).
# Link the static archives directly, in dependency order (C++ binding first,
# then the C core, then internal helpers). protobuf is linked via its own
# upstream config (grpcpp public headers include google/protobuf/*.h and
# grpc++_unsecure references protobuf::io::ZeroCopyInputStream symbols);
# abseil/c-ares/zlib come through CMakeDeps targets.
find_package(Protobuf CONFIG REQUIRED)
find_package(abseil-cpp REQUIRED)
find_package(c-ares REQUIRED)
find_package(zlib REQUIRED)

set(GRPC_LIBS
  ${LIBGRPC_UNSECURE_LIB_DIR}/libgrpc++_unsecure.a
  ${LIBGRPC_UNSECURE_LIB_DIR}/libgrpc_unsecure.a
  ${LIBGRPC_UNSECURE_LIB_DIR}/libgpr.a
  ${LIBGRPC_UNSECURE_LIB_DIR}/libupb_textformat_lib.a
  ${LIBGRPC_UNSECURE_LIB_DIR}/libupb_reflection_lib.a
  ${LIBGRPC_UNSECURE_LIB_DIR}/libupb_mini_descriptor_lib.a
  ${LIBGRPC_UNSECURE_LIB_DIR}/libupb_mini_table_lib.a
  ${LIBGRPC_UNSECURE_LIB_DIR}/libupb_message_lib.a
  ${LIBGRPC_UNSECURE_LIB_DIR}/libupb_wire_lib.a
  ${LIBGRPC_UNSECURE_LIB_DIR}/libupb_json_lib.a
  ${LIBGRPC_UNSECURE_LIB_DIR}/libupb_lex_lib.a
  ${LIBGRPC_UNSECURE_LIB_DIR}/libupb_hash_lib.a
  ${LIBGRPC_UNSECURE_LIB_DIR}/libupb_mem_lib.a
  ${LIBGRPC_UNSECURE_LIB_DIR}/libupb_descriptor_lib.a
  ${LIBGRPC_UNSECURE_LIB_DIR}/libupb_base_lib.a
  ${LIBGRPC_UNSECURE_LIB_DIR}/libutf8_range_lib.a
  ${LIBGRPC_UNSECURE_LIB_DIR}/libaddress_sorting.a
)

add_executable(test_package test_package.cpp)
target_include_directories(test_package PRIVATE ${LIBGRPC_UNSECURE_INC_DIR})
target_compile_features(test_package PRIVATE cxx_std_17)
target_link_libraries(test_package PRIVATE
  ${GRPC_LIBS}
  protobuf::libprotobuf
  abseil-cpp::abseil-cpp
  c-ares::c-ares
  zlib::zlib
)

include(CTest)
if(BUILD_TESTING)
  add_test(NAME test_package COMMAND test_package)
endif()
