# Consumer-side CMake project for plasma-wayland-protocols.
# Mirrors what kwayland5/5.116.0 does: a CONFIG-mode find_package that must
# yield PLASMA_WAYLAND_PROTOCOLS_DIR pointing at the installed protocol XMLs.
cmake_minimum_required(VERSION 3.16)
# C is enabled because the end-to-end flow below is a compiled consumer, not just
# a configure-time check.
project(plasma-wayland-protocols-consumer LANGUAGES C)

find_package(PlasmaWaylandProtocols 1.9.0 CONFIG REQUIRED)

if(NOT PLASMA_WAYLAND_PROTOCOLS_DIR)
  message(FATAL_ERROR "PLASMA_WAYLAND_PROTOCOLS_DIR is empty after find_package")
endif()
if(NOT IS_DIRECTORY "${PLASMA_WAYLAND_PROTOCOLS_DIR}")
  message(FATAL_ERROR "PLASMA_WAYLAND_PROTOCOLS_DIR does not exist: ${PLASMA_WAYLAND_PROTOCOLS_DIR}")
endif()

# Every protocol XML that kwayland5/5.116.0 consumes.
set(_pwp_protocols
    appmenu blur contrast dpms fake-input fullscreen-shell idle keystate
    output-management outputdevice plasma-shell plasma-virtual-desktop
    plasma-window-management remote-access server-decoration-palette
    server-decoration shadow slide surface-extension text-input
    text-input-unstable-v2 wayland-eglstream-controller)

set(_missing "")
foreach(_p IN LISTS _pwp_protocols)
  if(NOT EXISTS "${PLASMA_WAYLAND_PROTOCOLS_DIR}/${_p}.xml")
    list(APPEND _missing "${_p}.xml")
  endif()
endforeach()
if(_missing)
  message(FATAL_ERROR "consumer find_package: missing protocol XML(s): ${_missing}")
endif()

message(STATUS "FIND_PACKAGE_OK PLASMA_WAYLAND_PROTOCOLS_DIR=${PLASMA_WAYLAND_PROTOCOLS_DIR}")
message(STATUS "FIND_PACKAGE_OK all required protocol XML files present in the package tree")

# --- end-to-end consumer flow (rule-12 Hongmeng-specific test) ---------------
#
# A complete consumer use case rather than an assertion list: the protocol
# description this package installs is turned into code and then actually spoken
# over libwayland, which is what kwayland5 / kwin / libkscreen do with these
# files.  See e2e/plasma_e2e.c and e2e/gen_protocol.py.
#
# The bindings are generated at build time from
# ${PLASMA_WAYLAND_PROTOCOLS_DIR}/keystate.xml -- i.e. from the file the package
# really installs, resolved through its own CMake package config.  A missing or
# malformed XML, or a message the generator cannot translate exactly, fails the
# build instead of silently producing empty code.
find_package(Threads REQUIRED)

set(PWP_GEN_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")
if(NOT PWP_PYTHON)
  find_package(Python3 COMPONENTS Interpreter REQUIRED)
  set(PWP_PYTHON "${Python3_EXECUTABLE}")
endif()

add_custom_command(
  OUTPUT "${PWP_GEN_DIR}/keystate-protocol.h" "${PWP_GEN_DIR}/keystate-protocol.c"
  COMMAND "${CMAKE_COMMAND}" -E make_directory "${PWP_GEN_DIR}"
  COMMAND "${PWP_PYTHON}" "${CMAKE_CURRENT_SOURCE_DIR}/e2e/gen_protocol.py"
          "${PLASMA_WAYLAND_PROTOCOLS_DIR}/keystate.xml" "${PWP_GEN_DIR}"
  DEPENDS "${PLASMA_WAYLAND_PROTOCOLS_DIR}/keystate.xml"
          "${CMAKE_CURRENT_SOURCE_DIR}/e2e/gen_protocol.py"
  COMMENT "Generating keystate protocol bindings from the XML this package installs"
  VERBATIM)

# libwayland-client and libwayland-server are taken by explicit path (rather than
# as one aggregate target) because the published wayland package also ships
# libwayland-cursor.so / libwayland-egl.so, whose ELF the OHOS loader rejects --
# linking them would make this binary fail to start.  The flow only needs the
# client and server libraries.
add_executable(plasma_e2e e2e/plasma_e2e.c "${PWP_GEN_DIR}/keystate-protocol.c")
target_include_directories(plasma_e2e PRIVATE "${PWP_GEN_DIR}" "${PWP_WAYLAND_INCLUDE_DIR}")
target_link_libraries(plasma_e2e PRIVATE
    "${PWP_WAYLAND_LIB_DIR}/libwayland-client.so"
    "${PWP_WAYLAND_LIB_DIR}/libwayland-server.so"
    Threads::Threads)

enable_testing()
add_test(NAME plasma_keystate_e2e
         COMMAND plasma_e2e "${PLASMA_WAYLAND_PROTOCOLS_DIR}/keystate.xml")
set_tests_properties(plasma_keystate_e2e PROPERTIES TIMEOUT 180)
