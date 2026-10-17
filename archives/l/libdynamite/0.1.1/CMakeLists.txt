# Build description supplied by the Conan recipe.
#
# The upstream repository ships only configure.ac.in plus a bootstrap script
# that needs automake and libtoolize — neither exists on this platform — and
# checking in the generated autotools files would add tens of thousands of
# lines for what is three C files.  The upstream sources are used unchanged;
# only the build description lives here.  It produces the same artifacts
# upstream's autotools build does: libdynamite (static), the `dynamite`
# decompressor and the bundled `queen_extract` example tool.
cmake_minimum_required(VERSION 3.15)
project(libdynamite C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

include(GNUInstallDirs)

add_library(libdynamite lib/libdynamite.c)
set_target_properties(libdynamite PROPERTIES OUTPUT_NAME dynamite)
target_include_directories(libdynamite PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/lib>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)

add_executable(dynamite_cli src/dynamite.c)
set_target_properties(dynamite_cli PROPERTIES OUTPUT_NAME dynamite)
target_link_libraries(dynamite_cli PRIVATE libdynamite)

add_executable(queen_extract src/queen_extract.c)
target_link_libraries(queen_extract PRIVATE libdynamite)

install(TARGETS libdynamite dynamite_cli queen_extract
        RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
        ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR})
install(FILES lib/libdynamite.h DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
