cmake_minimum_required(VERSION 3.16)
project(test_mauikit LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Qml Quick QuickControls2)
# MauiKit4Targets references KF6::CoreAddons (PUBLIC link of the core
# library) but the upstream MauiKit4Config.cmake only finds Qt6Core, so the
# consumer has to resolve the KF6 dependency first (same pattern as kio).
find_package(KF6CoreAddons REQUIRED)
find_package(MauiKit4 REQUIRED CONFIG)

add_executable(test_mauikit test_mauikit.cpp)
# Upstream installs the export without a NAMESPACE, so the linkable target
# is plain `MauiKit4` (the `MauiKit4::Controls` alias only exists in the
# build tree).
target_link_libraries(test_mauikit PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Qml
    Qt6::Quick
    Qt6::QuickControls2
    MauiKit4)

if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    target_link_options(test_mauikit PRIVATE "-Wl,-rpath,$ORIGIN" "-Wl,--disable-new-dtags")
endif()

enable_testing()
# meta:     public C++ API export (version string + QML singleton meta objects)
add_test(NAME meta_objects COMMAND test_mauikit meta)
# defaults: OHOS adaptation defaults after the MauiMan patch + platform guards
add_test(NAME ohos_defaults COMMAND test_mauikit defaults)
# qml:      org.mauikit.controls plugin loads and a control instantiates offscreen
add_test(NAME qml_module COMMAND test_mauikit qml)
# qmltypes: BaseWindow decoration chain (Maui.WindowShadow / Maui.WindowControls,
#           both from platform-gated CMake sources) resolves; WindowShadow and
#           the real BaseWindow unit instantiate offscreen
add_test(NAME qml_window_types COMMAND test_mauikit qmltypes)
