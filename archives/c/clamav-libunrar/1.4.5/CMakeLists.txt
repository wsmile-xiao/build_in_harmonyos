cmake_minimum_required(VERSION 3.15)
project(clamunrar LANGUAGES C CXX)

include(GNUInstallDirs)

if(NOT DEFINED CLAMUNRAR_SOURCE_DIR)
  message(FATAL_ERROR "CLAMUNRAR_SOURCE_DIR is required")
endif()

add_subdirectory("${CLAMUNRAR_SOURCE_DIR}" "${CMAKE_BINARY_DIR}/libclamunrar")
