cmake_minimum_required(VERSION 3.15)
project(test_cyrus_sasl_gs2 C)

# CONFIG forces Conan's cyrus-sasl-gs2-config.cmake, which points at the
# package's own libsasl2 via absolute paths, so no system libsasl2 can
# leak in through CMake module mode.
find_package(cyrus-sasl-gs2 REQUIRED CONFIG)

add_executable(test_gs2 test_gs2.c)
target_link_libraries(test_gs2 PRIVATE cyrus-sasl-gs2::cyrus-sasl-gs2)
# Bake the package plugin dir in: the test pins it via sasl_set_path()
# (same pattern as the cyrus-sasl/2.1.28 test_package), so GS2 discovery
# does not depend on the SASL_PATH environment alone.
if(SASL_PLUGIN_DIR)
  target_compile_definitions(test_gs2 PRIVATE SASL_PLUGIN_DIR="${SASL_PLUGIN_DIR}")
endif()

enable_testing()
add_test(NAME test_gs2 COMMAND test_gs2)
