cmake_minimum_required(VERSION 3.15)
project(clay C)

# Clay is a single-header library: exactly one translation unit must
# define CLAY_IMPLEMENTATION before including clay.h. We build that TU
# into a static library so consumers just link clay::clay (the header
# then behaves as a regular declaration-only include).
#
# CLAY_SRC_DIR points at the extracted upstream source tree (passed by
# the recipe); this packaging project lives beside it in the build
# folder, NOT inside the source tree (the upstream root has its own
# CMakeLists that would pull every example via FetchContent).
set(CLAY_SRC_DIR "${CLAY_SRC_DIR}" CACHE PATH "clay upstream source tree")
add_library(clay STATIC ${CMAKE_CURRENT_SOURCE_DIR}/../../clay_impl.c)
target_include_directories(clay PUBLIC ${CLAY_SRC_DIR})
target_include_directories(clay PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    $<INSTALL_INTERFACE:include>)
# clay.h compiles cleanly as C11
set_target_properties(clay PROPERTIES C_STANDARD 11)

include(GNUInstallDirs)
install(TARGETS clay
        ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR})
install(FILES ${CLAY_SRC_DIR}/clay.h
        DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
