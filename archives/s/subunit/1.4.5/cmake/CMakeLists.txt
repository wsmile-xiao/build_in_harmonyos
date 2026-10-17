cmake_minimum_required(VERSION 3.15)
project(subunit C)

# Minimal build script contributed by the OHOS PC packaging recipe: upstream
# 1.4.5 ships only autotools inputs (configure.ac, no generated configure),
# and regenerating it would require an autotools chain that the OHOS build
# hosts do not provide.  The C binding is a single translation unit, so a
# plain CMake wrapper around it is exact and reviewable.

add_library(subunit c/lib/child.c)
target_include_directories(subunit PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/c/include)
set_target_properties(subunit PROPERTIES
    OUTPUT_NAME subunit
    VERSION 1.4.5
    SOVERSION 0)
if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
    # Generic HarmonyOS CMake rules omit the usual SONAME flag.
    target_link_options(subunit PRIVATE "-Wl,-soname,libsubunit.so")
endif()

enable_testing()
add_executable(test_child c/tests/test_child.c)
target_include_directories(test_child PRIVATE ${CHECK_HEADERS})
target_link_libraries(test_child PRIVATE subunit ${CHECK_STATIC_ARCHIVE})
if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
    target_link_options(test_child PRIVATE "-Wl,-rpath,$ORIGIN")
endif()
if(UNIX)
    target_link_libraries(test_child PRIVATE m rt pthread)
endif()
add_test(NAME upstream-child COMMAND test_child)

include(GNUInstallDirs)
install(TARGETS subunit
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
        ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})
install(FILES c/include/subunit/child.h
        DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/subunit)
