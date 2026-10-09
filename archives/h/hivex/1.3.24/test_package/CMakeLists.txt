cmake_minimum_required(VERSION 3.15)
project(test_hivex C)

find_package(hivex REQUIRED)

add_executable(test_hivex test_hivex.c)
target_link_libraries(test_hivex hivex::hivex)

# The registry image used as the producer's starting point.  Upstream cannot
# create a hive from scratch, so the byte-identical upstream images/minimal
# image ships with the recipe.  It is stored as base64 TEXT (minimal.b64)
# because binary fixtures cannot be applied through the PR .diff; the test
# decodes it to a real hive image at runtime.  Copy it next to the test binary
# and run the test from the build directory.
configure_file(minimal.b64 ${CMAKE_CURRENT_BINARY_DIR}/minimal.b64 COPYONLY)

enable_testing()
add_test(NAME test_hivex
         COMMAND test_hivex minimal.b64 hivex-test-out.hive
         WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})
