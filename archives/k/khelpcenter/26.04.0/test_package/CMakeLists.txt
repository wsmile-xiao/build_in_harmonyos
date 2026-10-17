cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)
find_package(KF6Config REQUIRED)
find_package(KF6CoreAddons REQUIRED)
find_package(KF6I18n REQUIRED)

# The khelpcenter package uses cmake_find_mode=none: locate the
# khcdocmetainfo library and its headers explicitly.
find_path(KHC_INCLUDE_DIR docmetainfo.h
          HINTS "${KHC_INCLUDE_DIR}")
find_library(KHC_LIBRARY khcdocmetainfo
             HINTS "${KHC_LIB_DIR}")

add_executable(test_khelpcenter test_package.cpp)
target_include_directories(test_khelpcenter PRIVATE ${KHC_INCLUDE_DIR})
target_link_libraries(test_khelpcenter PRIVATE
    ${KHC_LIBRARY}
    Qt6::Core
    Qt6::Gui
    Qt6::Widgets
    KF6::ConfigGui
    KF6::CoreAddons
    KF6::I18n
)

enable_testing()
add_test(NAME test_khelpcenter COMMAND test_khelpcenter)
