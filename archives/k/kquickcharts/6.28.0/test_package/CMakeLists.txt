cmake_minimum_required(VERSION 3.16)
project(test_kquickcharts CXX)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS Core Qml Quick)

add_executable(test_kquickcharts test_kquickcharts.cpp)
target_link_libraries(test_kquickcharts PRIVATE Qt6::Qml Qt6::Quick)

# kquickcharts is a QML module (no public C++ headers). Link the packaged
# shared library to prove the artifact is linkable and loaded at runtime.
add_library(kquickcharts_shared UNKNOWN IMPORTED)
set_target_properties(kquickcharts_shared PROPERTIES
    IMPORTED_LOCATION "${KQUICKCHARTS_LIB_DIR}/libQuickCharts.so")
target_link_libraries(test_kquickcharts PRIVATE kquickcharts_shared)

if(TARGET Qt6::Core)
    target_link_libraries(test_kquickcharts PRIVATE Qt6::Core)
endif()

set_property(TARGET test_kquickcharts PROPERTY CXX_STANDARD 17)
set_property(TARGET test_kquickcharts PROPERTY CXX_STANDARD_REQUIRED ON)
