cmake_minimum_required(VERSION 3.15)
project(test_libarcus LANGUAGES CXX)

# protobuf/3.17.3 uses cmake_find_mode=none: CMakeDeps generates no
# Protobuf config, so load the native config first (via Protobuf_DIR /
# protobuf_DIR hints from test_package/conanfile.py). This provides
# protobuf::libprotobuf before ArcusConfig's find_dependency(Protobuf)
# runs (precedent: libarrow_flight test_package loads native gRPC/protobuf
# configs before the generated consumer config).
# zlib/1.3.1.1 (adapted Autotools RREV) exposes ZLIB::ZLIB via CMakeDeps,
# but native protobuf-targets.cmake validates zlib::zlib (lowercase) at
# include time (protobuf-targets.cmake:69) and fails the whole configure
# when it is missing. Load the Conan ZLIB config first, then alias the
# lowercase name BEFORE find_package(Protobuf) so the check passes.
find_package(ZLIB CONFIG QUIET)
if(NOT TARGET zlib::zlib)
  if(TARGET ZLIB::ZLIB)
    add_library(zlib::zlib INTERFACE IMPORTED)
    set_property(TARGET zlib::zlib APPEND PROPERTY INTERFACE_LINK_LIBRARIES ZLIB::ZLIB)
  elseif(DEFINED HMBS_ZLIB_PACKAGE_DIR)
    add_library(zlib::zlib UNKNOWN IMPORTED)
    set_target_properties(zlib::zlib PROPERTIES
      IMPORTED_LOCATION "${HMBS_ZLIB_PACKAGE_DIR}/lib/libz.a"
      INTERFACE_INCLUDE_DIRECTORIES "${HMBS_ZLIB_PACKAGE_DIR}/include")
  endif()
endif()
find_package(Protobuf CONFIG REQUIRED)
# Conan's generated Arcus config links the aggregate target
# protobuf::protobuf, but protobuf/3.17.3 native config (cmake_find_mode=none)
# only provides protobuf::libprotobuf. Alias the aggregate name to the real
# imported target before ArcusTargets.cmake is included.
if(NOT TARGET protobuf::protobuf)
  if(TARGET protobuf::libprotobuf)
    add_library(protobuf::protobuf INTERFACE IMPORTED)
    set_property(TARGET protobuf::protobuf APPEND PROPERTY INTERFACE_LINK_LIBRARIES protobuf::libprotobuf)
  endif()
endif()
find_package(Arcus CONFIG REQUIRED)

add_executable(test_socket test_socket.cpp)
target_compile_features(test_socket PRIVATE cxx_std_17)
target_link_libraries(test_socket PRIVATE Arcus)

add_executable(test_error test_error.cpp)
target_compile_features(test_error PRIVATE cxx_std_17)
target_link_libraries(test_error PRIVATE Arcus)

add_executable(upstream_smoke upstream_test.cpp)
target_compile_features(upstream_smoke PRIVATE cxx_std_17)
target_link_libraries(upstream_smoke PRIVATE Arcus)

# Upstream regression smoke: verbatim upstream test_package/test.cpp (tag 5.0.0).
# NOTE: no enable_testing()/add_test() here on purpose. The two consumer
# binaries above are executed directly by test_package/conanfile.py via
# self.run() (counts feed HMBS_TEST_PACKAGE_RESULT), and upstream_test.cpp is
# executed as ./upstream_smoke (counts feed HMBS_UPSTREAM_TEST_RESULT).
# Registering ctest entries would create a false ctest inventory that the
# evidence gate misreads as additional upstream tests.
