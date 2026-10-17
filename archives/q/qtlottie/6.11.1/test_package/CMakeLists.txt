cmake_minimum_required(VERSION 3.16)
project(test_qtlottie CXX)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS Lottie Core Gui Qml Quick)

add_executable(test_qtlottie test_qtlottie.cpp)
target_link_libraries(test_qtlottie PRIVATE Qt6::Lottie)

if(TARGET Qt6::Core)
    target_link_libraries(test_qtlottie PRIVATE Qt6::Core)
endif()
if(TARGET Qt6::Gui)
    target_link_libraries(test_qtlottie PRIVATE Qt6::Gui)
endif()
if(TARGET Qt6::Qml)
    target_link_libraries(test_qtlottie PRIVATE Qt6::Qml)
endif()
if(TARGET Qt6::Quick)
    target_link_libraries(test_qtlottie PRIVATE Qt6::Quick)
endif()

set_property(TARGET test_qtlottie PROPERTY CXX_STANDARD 17)
set_property(TARGET test_qtlottie PROPERTY CXX_STANDARD_REQUIRED ON)
