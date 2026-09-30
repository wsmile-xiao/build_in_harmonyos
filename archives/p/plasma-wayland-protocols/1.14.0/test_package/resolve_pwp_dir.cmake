# Evaluates the native PlasmaWaylandProtocolsConfig.cmake in script mode and
# emits the PLASMA_WAYLAND_PROTOCOLS_DIR it defines.
#   cmake -DPWP_CONFIG=<...>/PlasmaWaylandProtocolsConfig.cmake \
#         -DPWP_OUT=<file> -P resolve_pwp_dir.cmake
cmake_minimum_required(VERSION 3.16)
if(NOT DEFINED PWP_CONFIG)
  message(FATAL_ERROR "PWP_CONFIG not provided")
endif()
include("${PWP_CONFIG}")
if(NOT DEFINED PLASMA_WAYLAND_PROTOCOLS_DIR OR NOT PLASMA_WAYLAND_PROTOCOLS_DIR)
  message(FATAL_ERROR "PLASMA_WAYLAND_PROTOCOLS_DIR not defined by ${PWP_CONFIG}")
endif()
if(DEFINED PWP_OUT)
  file(WRITE "${PWP_OUT}" "${PLASMA_WAYLAND_PROTOCOLS_DIR}")
else()
  message("PWP_DIR=${PLASMA_WAYLAND_PROTOCOLS_DIR}")
endif()
