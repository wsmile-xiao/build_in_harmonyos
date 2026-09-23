cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# KCddb6Targets.cmake transitively references KF6Config (Qt6::Gui) and
# Qt6::Network, so load Qt6 first.
find_package(Qt6 REQUIRED COMPONENTS Core Network Gui Widgets)
find_package(KF6Config REQUIRED)
find_package(KF6CoreAddons REQUIRED)
find_package(KF6I18n REQUIRED)

# audiocdplugins installs headers under include/audiocdplugins
find_path(AUDIOCDPLUGINS_INCLUDE_DIR audiocdencoder.h
          PATH_SUFFIXES audiocdplugins)

# KCddb6 (libkcddb) uses cmake_find_mode=none, so its include dir has to be
# located explicitly (the audiocdplugins headers include <kcddb/CDInfo>).
find_path(KCDDB_INCLUDE_DIR kcddb/CDInfo
          PATH_SUFFIXES KCddb6
          NO_DEFAULT_PATH
          PATHS "${CONAN_LIBKCDDB_INCLUDE}")

add_executable(test_package test_package.cpp)
target_include_directories(test_package PRIVATE
    ${AUDIOCDPLUGINS_INCLUDE_DIR}
    ${KCDDB_INCLUDE_DIR}
)

# The audiocdplugins library (AudioCDDataSink vtable/dtor live there) and
# KCddb6 (CDInfo) are consumed via plain find_library; the audiocd package
# uses cmake_find_mode=none so no CMakeDeps target exists.
find_library(AUDIOCDPLUGINS_LIBRARY audiocdplugins
             HINTS "${CONAN_AUDIOCD_LIB}")
find_library(KCDDB_LIBRARY KCddb6
             HINTS "${CONAN_LIBKCDDB_LIB}")

# QLibrary / qDeleteAll
target_link_libraries(test_package PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Widgets
    KF6::ConfigCore
    KF6::CoreAddons
    KF6::I18n
    ${AUDIOCDPLUGINS_LIBRARY}
    ${KCDDB_LIBRARY}
)
