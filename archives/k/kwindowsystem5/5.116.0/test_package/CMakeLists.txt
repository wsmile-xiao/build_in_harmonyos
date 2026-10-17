cmake_minimum_required(VERSION 3.16)
project(test_kwindowsystem5 CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps.
# kwindowsystem ships KF5::WindowSystem with the CMake config under
# lib/cmake/KF5WindowSystem (cmake_file_name KF5WindowSystem).
find_package(KF5WindowSystem REQUIRED)
find_package(Qt5 REQUIRED COMPONENTS Core Gui Widgets)

add_executable(test_kwindowsystem5 test.cpp)
target_link_libraries(test_kwindowsystem5
    KF5::WindowSystem
    Qt5::Core
    Qt5::Gui
    Qt5::Widgets
)

enable_testing()
add_test(NAME test_kwindowsystem5 COMMAND test_kwindowsystem5)
