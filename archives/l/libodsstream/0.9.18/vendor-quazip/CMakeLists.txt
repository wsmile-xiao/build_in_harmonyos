# Vendored QuaZip 1.4 top-level build (Qt6) for the libodsstream recipe.
# Mirrors the upstream quazip-1.4 top-level CMakeLists.txt variable setup
# (QUAZIP_LIB_VERSION/SOVERSION, Qt major selection) but installs nothing
# (QUAZIP_INSTALL=OFF) — the libodsstream recipe consumes the built static
# archive through a QuaZip-Qt6Config.cmake shim written next to the build.
cmake_minimum_required(VERSION 3.15)

project(QuaZip VERSION 1.4)

set(QUAZIP_LIB_VERSION ${QuaZip_VERSION})
set(QUAZIP_LIB_SOVERSION 1)

set(CMAKE_AUTOMOC ON)
set(CMAKE_INCLUDE_CURRENT_DIR ON)

option(QUAZIP_BZIP2 "Enables BZIP2 compression" OFF)
option(QUAZIP_INSTALL "Install QuaZip" OFF)
set(QUAZIP_QT_MAJOR_VERSION 6 CACHE STRING "Qt version to use")

set(QUAZIP_SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR})
set(QUAZIP_BINARY_DIR ${CMAKE_CURRENT_BINARY_DIR})
set(QUAZIP_LIB_FILE_NAME quazip1-qt${QUAZIP_QT_MAJOR_VERSION})
set(QUAZIP_LIB_TARGET_NAME QuaZip)
set(QUAZIP_DIR_NAME QuaZip-Qt${QUAZIP_QT_MAJOR_VERSION}-${QUAZIP_LIB_VERSION})
set(QUAZIP_PACKAGE_NAME QuaZip-Qt${QUAZIP_QT_MAJOR_VERSION})

find_package(Qt6 REQUIRED COMPONENTS Core Core5Compat)
set(QUAZIP_LIB_LIBRARIES Qt6::Core Qt6::Core5Compat)

find_package(zlib REQUIRED)  # conan CMakeDeps target is zlib::zlib
set(QUAZIP_LIB_LIBRARIES ${QUAZIP_LIB_LIBRARIES} zlib::zlib)

set(QUAZIP_DEP)
set(QUAZIP_INC)
set(QUAZIP_LIB)
set(QUAZIP_LBD)

add_subdirectory(quazip)
