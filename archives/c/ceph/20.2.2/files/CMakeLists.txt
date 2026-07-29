cmake_minimum_required(VERSION 3.16)
project(ceph_crush VERSION 20.2.2 LANGUAGES C)

include(CTest)
include(GNUInstallDirs)

if(NOT DEFINED CEPH_SOURCE_DIR)
  message(FATAL_ERROR "CEPH_SOURCE_DIR must point to the unpacked Ceph source")
endif()

set(CEPH_CRUSH_DIR "${CEPH_SOURCE_DIR}/src/crush")
if(NOT EXISTS "${CEPH_CRUSH_DIR}/builder.c")
  message(FATAL_ERROR "Ceph CRUSH sources were not found in ${CEPH_CRUSH_DIR}")
endif()

set(CEPH_GENERATED_ROOT "${CMAKE_CURRENT_BINARY_DIR}/generated")
# Ceph 20.2.2 CRUSH headers include "include/int_types.h" verbatim.
# Keep the generated root as the search path and preserve that subpath.
file(MAKE_DIRECTORY "${CEPH_GENERATED_ROOT}/include")
configure_file(
  "${CMAKE_CURRENT_LIST_DIR}/int_types.h.in"
  "${CEPH_GENERATED_ROOT}/include/int_types.h"
  COPYONLY
)

add_library(
  ceph_crush STATIC
  "${CEPH_CRUSH_DIR}/builder.c"
  "${CEPH_CRUSH_DIR}/crush.c"
  "${CEPH_CRUSH_DIR}/hash.c"
  "${CEPH_CRUSH_DIR}/mapper.c"
)
target_compile_features(ceph_crush PUBLIC c_std_99)
target_include_directories(
  ceph_crush
  PUBLIC
    "$<BUILD_INTERFACE:${CEPH_GENERATED_ROOT}>"
    "$<BUILD_INTERFACE:${CEPH_SOURCE_DIR}/src>"
    "$<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>"
)
if(NOT WIN32)
  target_link_libraries(ceph_crush PUBLIC m)
endif()

install(
  TARGETS ceph_crush
  ARCHIVE DESTINATION "${CMAKE_INSTALL_LIBDIR}"
)
install(
  FILES
    "${CEPH_CRUSH_DIR}/builder.h"
    "${CEPH_CRUSH_DIR}/crush.h"
    "${CEPH_CRUSH_DIR}/crush_compat.h"
    "${CEPH_CRUSH_DIR}/hash.h"
    "${CEPH_CRUSH_DIR}/mapper.h"
  DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}/crush"
)
# Consumers search from <prefix>/include, so the upstream include spelling
# resolves to <prefix>/include/include/int_types.h.
install(
  FILES
    "${CEPH_GENERATED_ROOT}/include/int_types.h"
  DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}/include"
)

if(BUILD_TESTING)
  add_executable(
    ceph_crush_upstream_test
    "${CMAKE_CURRENT_LIST_DIR}/upstream_crush_test.c"
  )
  target_link_libraries(ceph_crush_upstream_test PRIVATE ceph_crush)

  foreach(
    scenario
    IN ITEMS
      firstn_basic
      firstn_toosmall
      firstn_single_out_first
      straw2_distribution
  )
    add_test(
      NAME "ceph_crush_${scenario}"
      COMMAND ceph_crush_upstream_test "${scenario}"
    )
  endforeach()
endif()
