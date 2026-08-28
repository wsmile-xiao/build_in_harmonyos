cmake_minimum_required(VERSION 3.15)
project(libschrift LANGUAGES C)

set(LIBSCHRIFT_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src")

add_library(schrift "${LIBSCHRIFT_SOURCE_DIR}/schrift.c")
target_include_directories(schrift PUBLIC
    $<BUILD_INTERFACE:${LIBSCHRIFT_SOURCE_DIR}>
    $<INSTALL_INTERFACE:include>)
target_compile_features(schrift PRIVATE c_std_99)

add_executable(libschrift_stress "${LIBSCHRIFT_SOURCE_DIR}/stress.c")
target_include_directories(libschrift_stress PRIVATE "${LIBSCHRIFT_SOURCE_DIR}")
target_link_libraries(libschrift_stress PRIVATE schrift m)

include(GNUInstallDirs)
install(TARGETS schrift
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
install(FILES "${LIBSCHRIFT_SOURCE_DIR}/schrift.h" DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(FILES "${LIBSCHRIFT_SOURCE_DIR}/schrift.3" DESTINATION ${CMAKE_INSTALL_MANDIR}/man3)
