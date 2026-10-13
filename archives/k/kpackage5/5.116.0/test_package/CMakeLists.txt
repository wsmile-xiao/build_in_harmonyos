cmake_minimum_required(VERSION 3.16)
project(test_kpackage5 CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(${CMAKE_CURRENT_LIST_DIR}/../generators/conan_cmakedeps_paths.cmake
        OPTIONAL)

find_package(Qt5 5.15.2 REQUIRED NO_MODULE COMPONENTS Core)
find_package(KF5Package REQUIRED NO_MODULE)
find_package(KF5CoreAddons REQUIRED NO_MODULE)

add_executable(test_kpackage5 test_kpackage5.cpp)
target_link_libraries(test_kpackage5 PRIVATE KF5::Package KF5::CoreAddons Qt5::Core)
