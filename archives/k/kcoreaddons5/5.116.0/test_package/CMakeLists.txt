cmake_minimum_required(VERSION 3.16)
project(KCoreAddons5TestPackage CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt5Core CONFIG REQUIRED)

# Consumers use the installed KF5CoreAddonsConfig.cmake (cmake_find_mode=none).
find_package(KF5CoreAddons CONFIG REQUIRED)

add_executable(test_kcoreaddons5 test.cpp)
target_link_libraries(test_kcoreaddons5 KF5::CoreAddons Qt5::Core)

enable_testing()
add_test(NAME test_kcoreaddons5 COMMAND test_kcoreaddons5)
