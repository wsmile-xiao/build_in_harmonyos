cmake_minimum_required(VERSION 3.15)
project(test_dbus C)
find_package(dbus CONFIG REQUIRED)
add_executable(test_dbus test.c)
target_link_libraries(test_dbus PRIVATE dbus::dbus)
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    target_link_options(test_dbus PRIVATE -stdlib=libc++)
endif()
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" AND DEFINED OHOS_CXX_RUNTIME_DIR)
    target_link_libraries(test_dbus PRIVATE
        "${OHOS_CXX_RUNTIME_DIR}/libc++.so"
        "${OHOS_CXX_RUNTIME_DIR}/libc++abi.a"
        "${OHOS_CXX_RUNTIME_DIR}/libunwind.a"
    )
endif()
enable_testing()
add_test(NAME test_dbus COMMAND $<TARGET_FILE:test_dbus>)
