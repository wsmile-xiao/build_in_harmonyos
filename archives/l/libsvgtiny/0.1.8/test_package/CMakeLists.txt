cmake_minimum_required(VERSION 3.15)
project(test_libsvgtiny C)

# Find the package via Conan-generated CMakeDeps
find_package(LibSvgTiny REQUIRED)

# Consumer smoke test: inline SVG through svgtiny_create/parse/free
add_executable(test_svgtiny test.c)
target_link_libraries(test_svgtiny LibSvgTiny::svgtiny)

# Upstream test harness (vendored from libsvgtiny-0.1.8/test/decode_svg.c).
# decode_svg.c uses `#include "svgtiny.h"`; quoted include falls back to the
# package include dir provided by LibSvgTiny::svgtiny.
add_executable(test_decode_svg upstream/decode_svg.c)
target_link_libraries(test_decode_svg LibSvgTiny::svgtiny)

enable_testing()
add_test(NAME test_svgtiny COMMAND test_svgtiny)

# Upstream functional regression: each vendored test/data/*.svg is decoded by
# the vendored upstream harness (runtest.sh exit-0 semantics), one CTest case
# per file so the 12-case upstream coverage is visible to CTest/CI directly.
file(GLOB SVG_DATA_FILES "${CMAKE_CURRENT_SOURCE_DIR}/upstream/data/*.svg")
list(LENGTH SVG_DATA_FILES SVG_DATA_COUNT)

# Hard gate: the vendored upstream regression set is exactly the 12 files of
# upstream test/data/*.svg. If they are absent (e.g. not exported into the test
# build), fail configure instead of silently registering 0 cases — a green CI
# must never mean "no upstream case actually ran".
if(NOT SVG_DATA_COUNT EQUAL 12)
    message(FATAL_ERROR
        "vendored upstream data set incomplete: expected 12 *.svg under "
        "${CMAKE_CURRENT_SOURCE_DIR}/upstream/data, found ${SVG_DATA_COUNT}")
endif()
message(STATUS
    "libsvgtiny test_package: ${SVG_DATA_COUNT} upstream decode_* cases + test_svgtiny")

foreach(svg_file ${SVG_DATA_FILES})
    get_filename_component(svg_name "${svg_file}" NAME_WE)
    add_test(NAME decode_${svg_name}
             COMMAND test_decode_svg "${svg_file}" 1.0
                     "${CMAKE_CURRENT_BINARY_DIR}/${svg_name}.mvg")
    # Upstream decode_svg returns 0 even when svgtiny_parse fails (it only
    # prints to stderr), so exit-0 alone would let parse failures pass.
    # Fail the case on the harness's own error output (vendored source kept
    # byte-identical to upstream; the criterion is enforced here).
    # Exception: afl-expat-crash.svg is an AFL-found expat-crash PoC whose
    # regression purpose is "handled gracefully, no crash" — a graceful
    # svgtiny_parse failure IS the expected outcome for that input.
    if(NOT svg_name STREQUAL "afl-expat-crash")
        set_tests_properties(decode_${svg_name} PROPERTIES
            FAIL_REGULAR_EXPRESSION "svgtiny_create failed;svgtiny_parse failed;Unable to open")
    endif()
endforeach()
