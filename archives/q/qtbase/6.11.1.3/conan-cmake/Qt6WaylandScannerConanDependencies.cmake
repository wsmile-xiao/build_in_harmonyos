get_filename_component(_qtbase_prefix "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
set(WaylandScanner_EXECUTABLE "${_qtbase_prefix}/libexec/wayland-scanner")
if(TARGET Wayland::Scanner)
    set_target_properties(Wayland::Scanner PROPERTIES
        IMPORTED_LOCATION "${WaylandScanner_EXECUTABLE}")
endif()
unset(_qtbase_prefix)
