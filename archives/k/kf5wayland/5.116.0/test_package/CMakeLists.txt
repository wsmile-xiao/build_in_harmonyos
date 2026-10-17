cmake_minimum_required(VERSION 3.16)
project(test_kf5wayland LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# kf5wayland installs its own KF5WaylandConfig.cmake (cmake_find_mode=none
# in the recipe), so the canonical targets are KF5::WaylandClient /
# KF5::WaylandServer.
find_package(KF5Wayland 5.116.0 REQUIRED CONFIG)

if(NOT TARGET KF5::WaylandClient OR NOT TARGET KF5::WaylandServer)
    message(
        FATAL_ERROR
        "KF5::WaylandClient / KF5::WaylandServer targets not provided by "
        "KF5WaylandConfig.cmake"
    )
endif()

# The 5th (platform) assertion checks the packaged .so's ELF .codesign
# section, so pass the installed client library path into the test. The
# project's install(EXPORT) may emit the location per-configuration
# (KF5WaylandTargets-release.cmake sets IMPORTED_LOCATION_RELEASE) instead
# of the plain IMPORTED_LOCATION, so fall back through the config variants.
get_target_property(KF5WAYLAND_CLIENT_LIB KF5::WaylandClient IMPORTED_LOCATION)
if(NOT KF5WAYLAND_CLIENT_LIB)
    get_target_property(KF5WAYLAND_CLIENT_LIB KF5::WaylandClient IMPORTED_LOCATION_RELEASE)
endif()
if(NOT KF5WAYLAND_CLIENT_LIB)
    get_target_property(KF5WAYLAND_CLIENT_LIB KF5::WaylandClient IMPORTED_LOCATION_DEBUG)
endif()
if(NOT KF5WAYLAND_CLIENT_LIB)
    message(
        FATAL_ERROR
        "KF5::WaylandClient has no IMPORTED_LOCATION (plain or per-configuration); "
        "the .codesign platform assertion cannot run"
    )
endif()

add_executable(test_kf5wayland test_kf5wayland.cpp)
target_link_libraries(
    test_kf5wayland
    PRIVATE
        KF5::WaylandClient
        KF5::WaylandServer
)
target_compile_definitions(
    test_kf5wayland
    PRIVATE KF5_CLIENT_LIB_PATH="${KF5WAYLAND_CLIENT_LIB}"
)

enable_testing()
add_test(NAME test_kf5wayland COMMAND test_kf5wayland)
