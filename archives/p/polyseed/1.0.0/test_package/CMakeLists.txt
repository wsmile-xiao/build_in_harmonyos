cmake_minimum_required(VERSION 3.15)
project(test_polyseed C)

find_package(polyseed REQUIRED)

add_executable(test_polyseed test.c)
target_link_libraries(test_polyseed polyseed::polyseed)
# The consumer test exercises the same POLYSEED_PRIVATE APIs (encrypt/decrypt)
# as upstream's tests.c, which upstream only links against the static archive.
# POLYSEED_PKG_SHARED is passed from test_package/conanfile.py (recipe option).
if(POLYSEED_PKG_SHARED STREQUAL "True")
  message(FATAL_ERROR
    "polyseed consumer test uses POLYSEED_PRIVATE symbols (mirroring upstream "
    "tests.c); rebuild the package with the default option shared=False.")
endif()
target_compile_definitions(test_polyseed PRIVATE POLYSEED_STATIC)

enable_testing()
add_test(NAME test_polyseed COMMAND test_polyseed)
