cmake_minimum_required(VERSION 3.15)
project(libexsid VERSION 2.1 LANGUAGES C)

include(GNUInstallDirs)
find_package(libftdi1 CONFIG REQUIRED)
find_package(Threads REQUIRED)

add_library(exsid exSID.c exSID_ftdiwrap.c)
target_include_directories(exsid PRIVATE "${LIBFTDI_INCLUDE_DIR}")
add_library(libexsid::libexsid ALIAS exsid)
target_compile_options(exsid PRIVATE -Wall -fstrict-aliasing -DNDEBUG)
target_compile_definitions(exsid PRIVATE
    HAVE_DLFCN_H=1
    HAVE_FTDI=1
    EXSID_THREADED=1
    HAVE_PTHREAD_H=1
    HAVE_BUILTIN_EXPECT=1
    "SHLIBEXT=\".so\"")
target_include_directories(exsid
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
        $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)
target_link_libraries(exsid PRIVATE libftdi1::libftdi1 Threads::Threads ${CMAKE_DL_LIBS})
set_target_properties(exsid PROPERTIES
    OUTPUT_NAME exsid
    VERSION 2.0.0
    SOVERSION 2
    C_STANDARD 99
    C_STANDARD_REQUIRED YES)

install(TARGETS exsid
    EXPORT libexsidTargets
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    INCLUDES DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(FILES exSID.h DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})

# The upstream release contains no test suite. Keep an explicit check target
# so recipe logs record that the declared 0/0 upstream check was considered.
add_custom_target(check
    COMMAND ${CMAKE_COMMAND} -E echo "No upstream tests are declared (0/0)"
    VERBATIM)