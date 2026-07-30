cmake_minimum_required(VERSION 3.16)
project(memtool VERSION 2018.03.0 LANGUAGES C)

if(NOT MEMTOOL_SOURCE_DIR)
  message(FATAL_ERROR "MEMTOOL_SOURCE_DIR is required")
endif()

add_executable(memtool
  "${MEMTOOL_SOURCE_DIR}/memtool.c"
  "${MEMTOOL_SOURCE_DIR}/fileaccess.c"
  "${MEMTOOL_SOURCE_DIR}/acc_mmap.c"
)
target_include_directories(memtool PRIVATE "${MEMTOOL_SOURCE_DIR}")
target_compile_definitions(memtool PRIVATE
  _GNU_SOURCE
  "PACKAGE_STRING=\"memtool ${PROJECT_VERSION}\""
)
set_target_properties(memtool PROPERTIES C_STANDARD 99 C_STANDARD_REQUIRED YES)

include(GNUInstallDirs)
install(TARGETS memtool RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}")
install(
  FILES "${MEMTOOL_SOURCE_DIR}/memtool.1"
  DESTINATION "${CMAKE_INSTALL_MANDIR}/man1"
)
