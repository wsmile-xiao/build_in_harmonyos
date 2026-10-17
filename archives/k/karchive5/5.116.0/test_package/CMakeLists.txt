cmake_minimum_required(VERSION 3.16)
project(test_karchive5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Qt5 5.15.2 REQUIRED COMPONENTS Core)

# karchive5 installs its own KF5ArchiveConfig.cmake (cmake_find_mode=none in
# the recipe), so the canonical target is KF5::Archive.
find_package(KF5Archive 5.116.0 REQUIRED CONFIG)

if(NOT TARGET KF5::Archive)
    message(FATAL_ERROR "KF5::Archive target not provided by KF5ArchiveConfig.cmake")
endif()

add_executable(test_karchive5 test_karchive5.cpp)
target_link_libraries(test_karchive5 PRIVATE KF5::Archive Qt5::Core)

enable_testing()
add_test(NAME test_karchive5 COMMAND test_karchive5)
