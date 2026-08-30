# Test package for AstroMenace — real consumer test
# Verifies the CMake package target is usable and the binary is installed.
CMAKE_MINIMUM_REQUIRED(VERSION 3.15)
PROJECT(AstroMenaceTestPackage)

find_package(astromenace CONFIG REQUIRED)

# Resolve the package prefix (where the package was installed)
get_target_property(_astromenace_type astromenace::astromenace TYPE)
message(STATUS "astromenace::astromenace type = ${_astromenace_type}")

# For application packages, the Conan CMakeDeps generator sets the
# INTERFACE_INCLUDE_DIRECTORIES to the package's include dir (if any).
# The binary is installed to the bindirs path (bin/).
# We derive the expected binary path from the package root.
get_target_property(_astromenace_incdir astromenace::astromenace INTERFACE_INCLUDE_DIRECTORIES)
# Guard: a CMake "-NOTFOUND" sentinel is NOT a valid include path.  Treat
# missing DEFINED property or a -NOTFOUND/empty value the same as no include
# dir and fall back to the standard install layout instead of building an
# invalid (root/NOTFOUND) path.
if(DEFINED _astromenace_incdir AND NOT _astromenace_incdir STREQUAL "" AND
   NOT _astromenace_incdir MATCHES "-NOTFOUND$" AND IS_DIRECTORY "${_astromenace_incdir}")
  # Derive the package root from the include dir (package_root/include)
  get_filename_component(_astromenace_root "${_astromenace_incdir}" DIRECTORY)
  set(ASTROMENACE_BINARY "${_astromenace_root}/bin/AstroMenace")
else()
  # Fallback: assume standard install layout
  if(DEFINED CMAKE_PREFIX_PATH)
    set(ASTROMENACE_BINARY "${CMAKE_PREFIX_PATH}/bin/AstroMenace")
  else()
    set(ASTROMENACE_BINARY "")
  endif()
endif()

# Fail fast on missing target metadata: a -NOTFOUND derived path means the
# package target did not expose its include dirs/bindirs, so the consumer
# cannot locate the delivered artifacts — this is a real test failure, not a
# configuration detail.  (A valid derived path whose binary is absent on a
# cross-compile host is NOT a metadata failure: test_package.cpp reports a
# NOTE and still passes compile/link.)
if(ASTROMENACE_BINARY STREQUAL "" OR ASTROMENACE_BINARY MATCHES "-NOTFOUND")
  message(FATAL_ERROR "astromenace test_package: cannot determine AstroMenace binary path "
                      "(INTERFACE_INCLUDE_DIRECTORIES not DEFINED or -NOTFOUND). "
                      "Check astromenace::astromenace target metadata.")
endif()
message(STATUS "AstroMenace binary expected at: ${ASTROMENACE_BINARY}")

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE astromenace::astromenace)
get_filename_component(ASTROMENACE_BINDIR "${ASTROMENACE_BINARY}" DIRECTORY)

target_compile_definitions(test_package PRIVATE
  ASTROMENACE_BINARY="${ASTROMENACE_BINARY}"
  ASTROMENACE_BINDIR="${ASTROMENACE_BINDIR}")