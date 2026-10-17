cmake_minimum_required(VERSION 3.16)
project(test_kgraphviewer CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# KParts headers/targets come from the vendored kparts shipped inside the
# tested package; the graphviz C API comes from the conan graphviz package
# (linked via the bridge configured by the tested package's FindGraphviz
# module — here we resolve it the same way with the same cache variables
# provided by conan_cmakedeps_paths.cmake + the recipe toolchain).
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)
find_package(KF6XmlGui REQUIRED)
find_package(KF6Parts REQUIRED)

find_library(KGRAPHVIEWER_LIBRARY NAMES kgraphviewer)
if(NOT KGRAPHVIEWER_LIBRARY)
    message(FATAL_ERROR "libkgraphviewer not found in the tested package")
endif()

find_path(GRAPHVIZ_INCLUDE_DIR graphviz/gvc.h)
find_library(GRAPHVIZ_GVC_LIBRARY NAMES gvc)
find_library(GRAPHVIZ_CGRAPH_LIBRARY NAMES cgraph)
if(NOT GRAPHVIZ_INCLUDE_DIR OR NOT GRAPHVIZ_GVC_LIBRARY OR NOT GRAPHVIZ_CGRAPH_LIBRARY)
    message(FATAL_ERROR "graphviz headers/libraries not found for the consumer test")
endif()

add_executable(test_kgraphviewer test_kgraphviewer.cpp)
target_link_libraries(test_kgraphviewer
    KF6::Parts
    KF6::XmlGui
    Qt6::Widgets
    ${KGRAPHVIEWER_LIBRARY}
    ${GRAPHVIZ_GVC_LIBRARY}
    ${GRAPHVIZ_CGRAPH_LIBRARY}
)
target_include_directories(test_kgraphviewer PRIVATE ${GRAPHVIZ_INCLUDE_DIR})

enable_testing()
# OHOS: the working directory is prepared by the test_package conanfile
# (ohos-runtime/cwd/x, with ../../bin holding symlinks to every dependency
# library) because the published kconfig package records a cwd-relative
# DT_NEEDED (../../bin/libKF6ConfigCore.so) in libKF6ConfigGui.so.
add_test(NAME test_kgraphviewer COMMAND test_kgraphviewer
         WORKING_DIRECTORY "${CMAKE_BINARY_DIR}/ohos-runtime/cwd/x")
