cmake_minimum_required(VERSION 3.15)
project(pdfgen C)

# PDFGen is a single translation unit (pdfgen.c + pdfgen.h). The upstream
# Makefile only exists for maintainer checks (gcov/cppcheck/fuzz flags);
# packaging drives a minimal CMake build so the toolchain (compiler + ar)
# is selected by the Conan CMakeToolchain.
add_library(pdfgen STATIC pdfgen.c)
target_include_directories(pdfgen PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    $<INSTALL_INTERFACE:include>)

include(GNUInstallDirs)
install(TARGETS pdfgen
        ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR})
install(FILES pdfgen.h DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
