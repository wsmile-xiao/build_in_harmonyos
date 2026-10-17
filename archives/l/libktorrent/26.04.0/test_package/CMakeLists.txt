cmake_minimum_required(VERSION 3.16)
project(test_package LANGUAGES CXX)

# The KTorrent6Config.cmake find_dependency walk resolves through the
# conan-generated paths. Components referenced by KTorrent6's
# INTERFACE_LINK_LIBRARIES that need explicit consumer-side handling:
#  - Qt6Xml / Qt6Gui (Qt6 config components)
#  - Boost::boost (uppercase casing; the conan CMakeDeps generator
#    declares lowercase boost::boost only — bridge both)
#  - LibGcrypt::LibGcrypt (the upstream FindLibGcrypt module is not on
#    the consumer's module path; create the imported target from the
#    conan-provided libgcrypt package directly)
find_package(Qt6 REQUIRED COMPONENTS Core Network Xml Gui)
find_package(boost REQUIRED)  # conan CMakeDeps package name (lowercase)
if(NOT TARGET Boost::boost)
    add_library(Boost::boost INTERFACE IMPORTED)
    target_link_libraries(Boost::boost INTERFACE boost::boost)
endif()
find_package(libgcrypt REQUIRED)  # conan CMakeDeps package (lowercase)
if(NOT TARGET LibGcrypt::LibGcrypt)
    add_library(LibGcrypt::LibGcrypt INTERFACE IMPORTED)
    target_link_libraries(LibGcrypt::LibGcrypt INTERFACE libgcrypt::libgcrypt)
endif()
find_package(KTorrent6 REQUIRED CONFIG)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package KTorrent6)
set_target_properties(test_package PROPERTIES
    CXX_STANDARD 20
    CXX_STANDARD_REQUIRED ON)
