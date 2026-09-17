cmake_minimum_required(VERSION 3.18)
project(test_gsettings_qt LANGUAGES CXX)

# Qt6 Core 的原生 config 来自 qtbase 包（由 conanfile 的 CMAKE_PREFIX_PATH 提供）。
find_package(Qt6 6.11.1 REQUIRED COMPONENTS Core)

add_executable(test_gsettings_qt test_gsettings_qt.cpp)
target_compile_features(test_gsettings_qt PRIVATE cxx_std_17)
target_include_directories(test_gsettings_qt PRIVATE "${GSETTINGS_QT_INCLUDEDIR}")
target_link_libraries(test_gsettings_qt PRIVATE "${GSETTINGS_QT_LIBRARY}" Qt6::Core)
