find_package(libxkbcommon CONFIG QUIET)
if(NOT TARGET libxkbcommon::libxkbcommon)
    # Non-Conan installations still use Qt's original finder.
    include("${CMAKE_CURRENT_LIST_DIR}/../3rdparty/kwin/FindXKB.cmake")
    return()
endif()

set(XKB_VERSION "${libxkbcommon_VERSION_STRING}")
include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(XKB
    REQUIRED_VARS libxkbcommon_FOUND
    VERSION_VAR XKB_VERSION
    HANDLE_VERSION_RANGE)
if(XKB_FOUND AND NOT TARGET XKB::XKB)
    add_library(XKB::XKB INTERFACE IMPORTED)
    set_target_properties(XKB::XKB PROPERTIES
        INTERFACE_LINK_LIBRARIES libxkbcommon::libxkbcommon)
endif()
