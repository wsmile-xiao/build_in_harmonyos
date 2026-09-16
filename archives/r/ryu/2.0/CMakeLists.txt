cmake_minimum_required(VERSION 3.15)
project(ryu C)

# Upstream default cc_library target `//ryu` (see ryu/BUILD):
#   srcs = f2s.c, d2s.c (+ internal headers); hdrs = ryu.h
add_library(ryu ryu/d2s.c ryu/f2s.c)

target_include_directories(ryu
  PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    $<INSTALL_INTERFACE:include>)

set_target_properties(ryu PROPERTIES C_STANDARD 11)

install(TARGETS ryu
  LIBRARY DESTINATION lib
  ARCHIVE DESTINATION lib)

# Keep the upstream-relative include form (`#include "ryu/ryu.h"`,
# as used by the upstream tests) => installed as <prefix>/include/ryu/ryu.h
install(FILES ryu/ryu.h DESTINATION include/ryu)
