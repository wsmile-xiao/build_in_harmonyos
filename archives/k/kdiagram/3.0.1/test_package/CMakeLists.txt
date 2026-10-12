cmake_minimum_required(VERSION 3.16)
project(kdiagram_consumer_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Part 1: find the installed package through its own config files — the
# exact mechanism eventviews (KDE PIM) uses to link KChart, and what any
# KGantt consumer uses. Note: the upstream install(EXPORT) has no
# NAMESPACE, so the imported targets are the bare KChart6 / KGantt6.
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)
find_package(KChart6 REQUIRED CONFIG)
find_package(KGantt6 REQUIRED CONFIG)

add_executable(kdiagram_consumer_test main.cpp)
target_link_libraries(kdiagram_consumer_test PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Widgets
    KChart6
    KGantt6
)

enable_testing()
add_test(NAME kdiagram_consumer_test COMMAND kdiagram_consumer_test)
