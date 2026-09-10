# Adapt the published Conan aggregate package to Qt's component targets.
get_filename_component(_qtbase_prefix "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
if(NOT TARGET Wayland::Client OR NOT TARGET Wayland::Server
        OR NOT TARGET Wayland::Cursor OR NOT TARGET Wayland::Egl)
    find_package(wayland 1.22 CONFIG QUIET)
    if(TARGET wayland::wayland)
        foreach(_qtbase_component IN ITEMS Client Server)
            if(NOT TARGET Wayland::${_qtbase_component})
                add_library(Wayland::${_qtbase_component} INTERFACE IMPORTED)
                set_target_properties(Wayland::${_qtbase_component} PROPERTIES
                    INTERFACE_LINK_LIBRARIES wayland::wayland)
            endif()
        endforeach()
        if(NOT TARGET Wayland::Cursor)
            add_library(Wayland::Cursor SHARED IMPORTED)
            set_target_properties(Wayland::Cursor PROPERTIES
                IMPORTED_LOCATION "${_qtbase_prefix}/lib/libwayland-cursor.so.0"
                INTERFACE_LINK_LIBRARIES Wayland::Client)
        endif()
        if(NOT TARGET Wayland::Egl)
            find_library(_qtbase_wayland_egl NAMES wayland-egl REQUIRED)
            add_library(Wayland::Egl UNKNOWN IMPORTED)
            set_target_properties(Wayland::Egl PROPERTIES
                IMPORTED_LOCATION "${_qtbase_wayland_egl}"
                INTERFACE_LINK_LIBRARIES Wayland::Client)
        endif()
        unset(_qtbase_component)
    endif()
endif()

# This executable has been relocated and signed along with the Qt package.
unset(_qtbase_prefix)
include("${CMAKE_CURRENT_LIST_DIR}/Qt6WaylandScannerConanDependencies.cmake")
