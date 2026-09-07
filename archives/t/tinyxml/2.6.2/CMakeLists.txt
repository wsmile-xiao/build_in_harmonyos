cmake_minimum_required(VERSION 3.15)
project(tinyxml VERSION 2.6.2 LANGUAGES CXX)

option(TINYXML_USE_STL "Build TinyXML with STL support" ON)

add_library(tinyxml
    tinyxml.cpp
    tinyxmlparser.cpp
    tinyxmlerror.cpp
    tinystr.cpp
)

target_include_directories(tinyxml PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    $<INSTALL_INTERFACE:include>
)

set_target_properties(tinyxml PROPERTIES
    POSITION_INDEPENDENT_CODE ON
    PUBLIC_HEADER "tinyxml.h;tinystr.h"
)

if(TINYXML_USE_STL)
    target_compile_definitions(tinyxml PUBLIC TIXML_USE_STL)
endif()

include(GNUInstallDirs)

install(TARGETS tinyxml
    EXPORT tinyxmlTargets
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    PUBLIC_HEADER DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

install(EXPORT tinyxmlTargets
    FILE tinyxmlTargets.cmake
    NAMESPACE tinyxml::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/tinyxml
)
