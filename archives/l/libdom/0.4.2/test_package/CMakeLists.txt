cmake_minimum_required(VERSION 3.15)
project(test_libdom C)

# Find the package via Conan-generated CMakeDeps
find_package(LibDom REQUIRED)
# Transitive deps of static libdom.a (explicit find for header/import resolution)
find_package(LibParserUtils REQUIRED)
find_package(LibWapcaplet REQUIRED)
find_package(LibHubbub REQUIRED)
find_package(LibXml2 REQUIRED)

# ---------------------------------------------------------------------------
# 1. Consumer API smoke test (kept from the original recipe)
# ---------------------------------------------------------------------------
add_executable(test_libdom test.c)
target_link_libraries(test_libdom
    LibDom::dom
    LibParserUtils::parserutils
    LibWapcaplet::wapcaplet
    LibHubbub::hubbub
    LibXml2::LibXml2)

enable_testing()
add_test(NAME test_libdom COMMAND test_libdom)

# ---------------------------------------------------------------------------
# 2. W3C DOMTS (DOM Test Suite) runnable subset — vendored from the upstream
#    libdom 0.4.2 release tarball (test/testcases/tests/level1/core).
#
#    Pipeline (mirrors upstream test/Makefile + run-test.sh):
#      .xml testcase --(perl test/transform.pl + DOMTSHandler.pm, run OFFLINE
#      on the packaging host)--> .c fragment, vendored UNMODIFIED in
#      upstream/test/domts/.  testutils/*.{c,h} are the unmodified upstream
#      DOMTS harness (comparators/domtsasserts/foreach/list/load/utils).
#      The bare <xmlparser.h>/<parser.h>/<errors.h> includes in the harness
#      load.c are resolved through upstream/shim/*.h forwarding headers to the
#      binding headers installed by the libdom Conan package
#      (dom/bindings/{xml,hubbub}/*.h). No upstream test source is modified.
#
#    Each generated fragment has its own main(); each is built into a separate
#    executable and run from upstream/ (where the chdir("test/testcases/
#    tests/level1/core/files") data path resolves to the vendored fixtures).
# ---------------------------------------------------------------------------
set(DOMTS_TESTUTILS_DIR ${CMAKE_CURRENT_SOURCE_DIR}/upstream/test/testutils)
set(DOMTS_SHIM_DIR     ${CMAKE_CURRENT_SOURCE_DIR}/upstream/shim)
set(DOMTS_SRC_DIR      ${CMAKE_CURRENT_SOURCE_DIR}/upstream/test/domts)

file(GLOB DOMTS_FRAGMENTS ${DOMTS_SRC_DIR}/*.c)

if(DOMTS_FRAGMENTS)
  # Compile the shared harness once (the six .c testutils referenced by the
  # upstream Makefile), then link its objects into every fragment executable.
  add_library(domts_utils OBJECT
      ${DOMTS_TESTUTILS_DIR}/comparators.c
      ${DOMTS_TESTUTILS_DIR}/domtsasserts.c
      ${DOMTS_TESTUTILS_DIR}/foreach.c
      ${DOMTS_TESTUTILS_DIR}/list.c
      ${DOMTS_TESTUTILS_DIR}/load.c
      ${DOMTS_TESTUTILS_DIR}/utils.c)
  target_include_directories(domts_utils PRIVATE
      ${DOMTS_TESTUTILS_DIR}
      ${DOMTS_SHIM_DIR})
  target_link_libraries(domts_utils PRIVATE
      LibDom::dom
      LibParserUtils::parserutils
      LibWapcaplet::wapcaplet
      LibHubbub::hubbub
      LibXml2::LibXml2)

  foreach(frag ${DOMTS_FRAGMENTS})
    get_filename_component(frag_name ${frag} NAME_WE)
    add_executable(domts_${frag_name} ${frag})
    target_include_directories(domts_${frag_name} PRIVATE
        ${DOMTS_TESTUTILS_DIR}
        ${DOMTS_SHIM_DIR})
    target_link_libraries(domts_${frag_name} PRIVATE
        domts_utils
        LibDom::dom
        LibParserUtils::parserutils
        LibWapcaplet::wapcaplet
        LibHubbub::hubbub
        LibXml2::LibXml2)
    add_test(NAME domts_${frag_name} COMMAND domts_${frag_name})
  endforeach()
endif()
