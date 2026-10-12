cmake_minimum_required(VERSION 3.15)
project(test_qt5_qtsensors CXX)

# qt5-qtbase exposes its modules through the aggregate Qt5Config.cmake
# (Qt5::Core / Qt5::Gui targets). qt5-qtdeclarative adds Qt5::Qml via its
# own Qt5QmlConfig.cmake, and qt5-qtsensors adds Qt5::Sensors via its own
# Qt5SensorsConfig.cmake.
find_package(Qt5 CONFIG REQUIRED)
find_package(Qt5Qml CONFIG REQUIRED)
find_package(Qt5Sensors CONFIG REQUIRED)

add_executable(test_qt5_qtsensors test.cpp)
target_link_libraries(test_qt5_qtsensors PRIVATE
    Qt5::Sensors Qt5::Qml Qt5::Core)
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    target_link_options(test_qt5_qtsensors PRIVATE -stdlib=libc++)
endif()
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" AND DEFINED OHOS_CXX_RUNTIME_DIR)
    target_link_libraries(test_qt5_qtsensors PRIVATE
        "${OHOS_CXX_RUNTIME_DIR}/libc++.so"
        "${OHOS_CXX_RUNTIME_DIR}/libc++abi.a"
        "${OHOS_CXX_RUNTIME_DIR}/libunwind.a"
    )
endif()
enable_testing()
add_test(NAME test_qt5_qtsensors COMMAND $<TARGET_FILE:test_qt5_qtsensors>)
