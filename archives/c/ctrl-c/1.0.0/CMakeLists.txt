cmake_minimum_required(VERSION 3.15)
project(ctrl-c LANGUAGES CXX)

# The upstream tag ships no build system (README: "copy source files to your
# project"), so the recipe exports this CMake wrapper and configures it with
# build_script_folder=<recipe source folder>, mirroring libschrift 0.10.2.
set(CTRLC_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src")

add_library(ctrl-c "${CTRLC_SOURCE_DIR}/ctrl-c.cpp")
target_include_directories(ctrl-c PUBLIC
    $<BUILD_INTERFACE:${CTRLC_SOURCE_DIR}>
    $<INSTALL_INTERFACE:include>)
target_compile_features(ctrl-c PUBLIC cxx_std_11)

include(GNUInstallDirs)
install(TARGETS ctrl-c
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
install(FILES "${CTRLC_SOURCE_DIR}/ctrl-c.h" DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
