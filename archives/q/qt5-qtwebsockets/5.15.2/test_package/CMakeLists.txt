cmake_minimum_required(VERSION 3.15)
project(test_qt5_qtwebsockets CXX)

# qt5-qtbase exposes its modules through the aggregate Qt5Config.cmake
# (Qt5::Core / Qt5::Network targets). qt5-qtwebsockets adds the
# Qt5::WebSockets target via its own Qt5WebSocketsConfig.cmake.
find_package(Qt5 CONFIG REQUIRED)
find_package(Qt5WebSockets CONFIG REQUIRED)

add_executable(test_qt5_qtwebsockets test.cpp)
target_link_libraries(test_qt5_qtwebsockets PRIVATE
    Qt5::WebSockets Qt5::Core)
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    target_link_options(test_qt5_qtwebsockets PRIVATE -stdlib=libc++)
endif()
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" AND DEFINED OHOS_CXX_RUNTIME_DIR)
    target_link_libraries(test_qt5_qtwebsockets PRIVATE
        "${OHOS_CXX_RUNTIME_DIR}/libc++.so"
        "${OHOS_CXX_RUNTIME_DIR}/libc++abi.a"
        "${OHOS_CXX_RUNTIME_DIR}/libunwind.a"
    )
endif()
enable_testing()
add_test(NAME test_qt5_qtwebsockets COMMAND $<TARGET_FILE:test_qt5_qtwebsockets>)
