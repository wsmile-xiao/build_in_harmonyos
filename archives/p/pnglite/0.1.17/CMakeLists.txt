cmake_minimum_required(VERSION 3.15)
project(pnglite VERSION 0.1.17 LANGUAGES C)

find_package(zlib REQUIRED CONFIG)

# zlib/1.3.1 is distributed as a static-only system-name dependency. Keeping
# pnglite static avoids embedding non-PIC zlib objects in a shared library.
add_library(pnglite STATIC pnglite.c)
set_target_properties(pnglite PROPERTIES
  C_STANDARD 99
  C_STANDARD_REQUIRED ON
  POSITION_INDEPENDENT_CODE ON)
target_include_directories(pnglite PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
  $<INSTALL_INTERFACE:include>)
target_link_libraries(pnglite PRIVATE zlib::zlib)

install(TARGETS pnglite ARCHIVE DESTINATION lib)
install(FILES pnglite.h DESTINATION include)
