cmake_minimum_required(VERSION 3.16)
project(test_qtquicktimeline CXX)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS QuickTimeline Core Qml Quick)

add_executable(test_qtquicktimeline test_qtquicktimeline.cpp)
target_link_libraries(test_qtquicktimeline PRIVATE Qt6::QuickTimeline)

if(TARGET Qt6::Core)
    target_link_libraries(test_qtquicktimeline PRIVATE Qt6::Core)
endif()
if(TARGET Qt6::Qml)
    target_link_libraries(test_qtquicktimeline PRIVATE Qt6::Qml)
endif()
if(TARGET Qt6::Quick)
    target_link_libraries(test_qtquicktimeline PRIVATE Qt6::Quick)
endif()

set_property(TARGET test_qtquicktimeline PROPERTY CXX_STANDARD 17)
set_property(TARGET test_qtquicktimeline PROPERTY CXX_STANDARD_REQUIRED ON)
