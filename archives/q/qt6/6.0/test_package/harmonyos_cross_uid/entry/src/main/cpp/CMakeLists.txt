cmake_minimum_required(VERSION 3.16)
project(qt6uidprobe LANGUAGES CXX)

set(NATIVE_PROBE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../../../native")

add_library(qt6uidprobe SHARED
    napi_init.cpp
    "${NATIVE_PROBE_DIR}/socket_probe.cpp"
)
target_compile_features(qt6uidprobe PRIVATE cxx_std_17)
target_include_directories(qt6uidprobe PRIVATE "${NATIVE_PROBE_DIR}")
target_link_libraries(qt6uidprobe PUBLIC libace_napi.z.so)

# The Qt runtime is staged from the Conan package for the device-only QLocalServer
# cross-UID check. Keeping it under .ci_logs avoids committing duplicate binaries.
get_filename_component(QT6_HAP_RUNTIME_ROOT
    "${CMAKE_CURRENT_SOURCE_DIR}/../../../../../../.ci_logs/qt6-hap-runtime"
    ABSOLUTE)
set(QT6_CORE_LIBRARY "${QT6_HAP_RUNTIME_ROOT}/lib/libQt6Core.so.6.0.0")
set(QT6_NETWORK_LIBRARY "${QT6_HAP_RUNTIME_ROOT}/lib/libQt6Network.so.6.0.0")
if(EXISTS "${QT6_CORE_LIBRARY}" AND EXISTS "${QT6_NETWORK_LIBRARY}")
    target_sources(qt6uidprobe PRIVATE qt_local_socket_test.cpp)
    target_include_directories(qt6uidprobe PRIVATE "${QT6_HAP_RUNTIME_ROOT}/include")
    target_compile_definitions(qt6uidprobe PRIVATE QT6_HAP_WITH_QT=1)
    target_link_libraries(qt6uidprobe PRIVATE "${QT6_NETWORK_LIBRARY}" "${QT6_CORE_LIBRARY}")
    foreach(qt_library IN ITEMS libQt6Core.so.6.0.0 libQt6Core.so.6 libQt6Network.so.6.0.0 libQt6Network.so.6)
        string(REGEX REPLACE "\\.so\\.6(\\.0\\.0)?$" ".so.6.0.0" qt_library_source_name "${qt_library}")
        add_custom_command(TARGET qt6uidprobe POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                "${QT6_HAP_RUNTIME_ROOT}/lib/${qt_library_source_name}"
                "$<TARGET_FILE_DIR:qt6uidprobe>/${qt_library}")
    endforeach()
else()
    message(STATUS "Qt runtime is not staged; raw AF_UNIX probe remains available")
endif()
