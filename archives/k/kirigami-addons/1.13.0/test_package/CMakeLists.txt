cmake_minimum_required(VERSION 3.20)
project(test_kirigami_addons LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core Gui)
find_package(KF6KirigamiAddons REQUIRED CONFIG)

# NameUtils links Qt6::Gui (QColor) through KirigamiAddonsComponents which is
# part of the KF6KirigamiAddons exported target set.
add_executable(test_kirigami_addons test_kirigami_addons.cpp)
target_link_libraries(test_kirigami_addons PRIVATE
    Qt6::Core
    Qt6::Gui
    KirigamiAddonsComponents
)

enable_testing()
add_test(NAME test_kirigami_addons COMMAND test_kirigami_addons)
