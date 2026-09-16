cmake_minimum_required(VERSION 3.15)
project(marco_test_package C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)

# marcos recipe does not export a cmake_file_name / cmake_target_name, so the
# published libmarco-private.so is located manually.  The conanfile passes the
# tested package folder through MARCO_PACKAGE_ROOT.
if(NOT MARCO_PACKAGE_ROOT)
  message(FATAL_ERROR "MARCO_PACKAGE_ROOT is not set")
endif()

set(_marco_lib_hints
    "${MARCO_PACKAGE_ROOT}/lib"
    "${MARCO_PACKAGE_ROOT}/lib64"
    "${MARCO_PACKAGE_ROOT}")

find_library(MARCO_PRIVATE_LIBRARY
  NAMES marco-private
  HINTS ${_marco_lib_hints}
  NO_DEFAULT_PATH)

if(NOT MARCO_PRIVATE_LIBRARY)
  # Fall back to an explicit glob: the package may only ship the versioned
  # soname (libmarco-private.so.2) with no unversioned dev symlink.
  file(GLOB _marco_candidates
       "${MARCO_PACKAGE_ROOT}/lib/libmarco-private.so*"
       "${MARCO_PACKAGE_ROOT}/lib64/libmarco-private.so*")
  foreach(_candidate ${_marco_candidates})
    if(NOT IS_SYMLINK "${_candidate}")
      set(MARCO_PRIVATE_LIBRARY "${_candidate}")
    endif()
  endforeach()
  if(NOT MARCO_PRIVATE_LIBRARY AND _marco_candidates)
    list(GET _marco_candidates 0 MARCO_PRIVATE_LIBRARY)
  endif()
endif()

if(NOT MARCO_PRIVATE_LIBRARY)
  message(FATAL_ERROR "libmarco-private not found under ${MARCO_PACKAGE_ROOT}")
endif()
message(STATUS "marco test: linking ${MARCO_PRIVATE_LIBRARY}")

# The installed private headers are NOT included by the consumers (they pull in
# <gtk/gtk.h>); the include dir is only added so the test tracks it.
file(GLOB _marco_hdr_candidates
     "${MARCO_PACKAGE_ROOT}/include/boxes.h"
     "${MARCO_PACKAGE_ROOT}/include/*/marco-private/boxes.h"
     "${MARCO_PACKAGE_ROOT}/include/*/boxes.h")
if(_marco_hdr_candidates)
  list(GET _marco_hdr_candidates 0 _marco_hdr)
  get_filename_component(MARCO_INCLUDE_DIR "${_marco_hdr}" DIRECTORY)
  message(STATUS "marco test: include dir ${MARCO_INCLUDE_DIR}")
endif()

add_library(marco_private SHARED IMPORTED)
set_target_properties(marco_private PROPERTIES
  IMPORTED_LOCATION "${MARCO_PRIVATE_LIBRARY}")

add_executable(marco_api_surface api_surface.c)
target_compile_options(marco_api_surface PRIVATE -Wall -Wextra)
target_link_libraries(marco_api_surface PRIVATE marco_private ${CMAKE_DL_LIBS})

add_executable(marco_geometry_contract geometry_contract.c)
target_compile_options(marco_geometry_contract PRIVATE -Wall -Wextra)
target_link_libraries(marco_geometry_contract PRIVATE marco_private)

add_executable(marco_no_display_guard no_display_guard.c)
target_compile_options(marco_no_display_guard PRIVATE -Wall -Wextra)
target_link_libraries(marco_no_display_guard PRIVATE marco_private ${CMAKE_DL_LIBS})

if(MARCO_INCLUDE_DIR)
  target_include_directories(marco_api_surface PRIVATE "${MARCO_INCLUDE_DIR}")
  target_include_directories(marco_geometry_contract PRIVATE "${MARCO_INCLUDE_DIR}")
  target_include_directories(marco_no_display_guard PRIVATE "${MARCO_INCLUDE_DIR}")
endif()
