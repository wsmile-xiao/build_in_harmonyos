cmake_minimum_required(VERSION 3.15)
project(test_libvips C)

enable_testing()

find_package(vips REQUIRED CONFIG)

add_executable(test_vips test_vips.c)
target_link_libraries(test_vips PRIVATE vips::vips)

# Vendored upstream tests (byte-for-byte from libvips 8.18.4 test/).
#   test_descriptors.c   -> upstream test 'descriptors'
#   test_token.c         -> upstream test 'token' (pure C, no fixture)
#   test_connections.c   -> upstream test 'connections' (source/target custom IO)
add_executable(test_descriptors upstream/test_descriptors.c)
target_link_libraries(test_descriptors PRIVATE vips::vips)
add_executable(test_token upstream/test_token.c)
target_link_libraries(test_token PRIVATE vips::vips)
add_executable(test_connections upstream/test_connections.c)
target_link_libraries(test_connections PRIVATE vips::vips)

# Consumer test with six PASS/FAIL checks.
add_test(NAME vips_consumer COMMAND test_vips)

# Generate a 64x64 black PNG through the vips pipeline; the vendored upstream C
# tests (descriptors, connections) consume it as their input fixture.
# test_descriptors.c crops 10-row bands at y=0 and y=20 (VIPS_ACCESS_RANDOM), so
# the fixture must be taller than 30 rows.
add_test(NAME gen_png COMMAND test_vips --gen-image ${CMAKE_CURRENT_BINARY_DIR}/test_64x64.png)

# Upstream 'descriptors': file descriptors closed on minimise/read/unref.
# Upstream drives test_descriptors.c from test_descriptors.sh; we run the same
# binary against a generated PNG (pngload_source is enabled in this package).
add_test(NAME upstream_descriptors COMMAND test_descriptors ${CMAKE_CURRENT_BINARY_DIR}/test_64x64.png)
set_tests_properties(upstream_descriptors PROPERTIES DEPENDS gen_png)
set_tests_properties(upstream_descriptors PROPERTIES SKIP_RETURN_CODE 77)

# Upstream 'connections': load via a custom VipsSource and save via a custom
# VipsTarget.  Upstream gates this on jpegload_source (disabled here); PNG uses
# the pngload_source path in the dependency chain instead, so we pass the
# generated PNG (no jpeg involved).
add_test(NAME upstream_connections COMMAND test_connections ${CMAKE_CURRENT_BINARY_DIR}/test_64x64.png ${CMAKE_CURRENT_BINARY_DIR}/conn_out.png)
set_tests_properties(upstream_connections PROPERTIES DEPENDS gen_png)

# Upstream 'token': the Meson test runs test/test_token.sh (a pure-shell
# wrapper, no python / no image fixture) against the ./test_token binary.
# test_token.sh is vendored byte-for-byte in upstream/ and executed from the
# build directory by the test_package conanfile after ctest; it needs the
# compiled test_token next to it, hence the executable target here.
# (The seven per-check ctest cases are intentionally not added: running the
# upstream wrapper reproduces the Meson 'token' test exactly.)
