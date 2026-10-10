cmake_minimum_required(VERSION 3.16)
project(KAuth5TestPackage CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# qt5-qtbase ships its own Qt5 config tree; the recipe-generated
# conan_cmakedeps_paths.cmake prepends the package prefixes so this resolves.
find_package(Qt5DBus CONFIG REQUIRED)

# Consumers use the installed KF5AuthConfig.cmake (cmake_find_mode=none).
find_package(KF5Auth CONFIG REQUIRED)

add_executable(test_kauth5 test.cpp)
target_link_libraries(test_kauth5 KF5::AuthCore Qt5::DBus Qt5::Core)

# HarmonyOS-specific behavioral test (new test, counted in the "鸿蒙特有测试"
# row of the PR test table).
add_executable(test_kauth5_ohos test_kauth5_ohos.cpp)
target_link_libraries(test_kauth5_ohos KF5::AuthCore Qt5::DBus Qt5::Core)

enable_testing()
add_test(NAME test_kauth5 COMMAND test_kauth5)
add_test(NAME test_kauth5_ohos COMMAND test_kauth5_ohos)
