cmake_minimum_required(VERSION 3.16)
project(test_kf5windowsystem LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# KF5WindowSystemConfig.cmake calls find_dependency(Qt5Gui 5.15.2) and
# find_dependency(Qt5Widgets 5.15.2), so the Qt5 components must resolve
# before KF5::WindowSystem is imported (the CMakeDeps-generated Qt5Config
# is the aggregated config for the qt5-qtbase package).
find_package(Qt5 5.15.2 REQUIRED COMPONENTS Core Gui Widgets)
find_package(KF5WindowSystem 5.116.0 REQUIRED)

add_executable(test_kf5windowsystem test_kf5windowsystem.cpp)
target_link_libraries(test_kf5windowsystem PRIVATE Qt5::Gui KF5::WindowSystem)

add_executable(test_kf5windowsystem_harmonyos test_kf5windowsystem_harmonyos.cpp)
target_link_libraries(test_kf5windowsystem_harmonyos PRIVATE Qt5::Gui KF5::WindowSystem)

if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
  foreach(_tgt test_kf5windowsystem test_kf5windowsystem_harmonyos)
    target_link_options(${_tgt} PRIVATE "-Wl,-rpath,$ORIGIN" "-Wl,--disable-new-dtags")
  endforeach()
endif()

enable_testing()
add_test(NAME test_kf5windowsystem COMMAND test_kf5windowsystem)
add_test(NAME kf5windowsystem_harmonyos_platform COMMAND test_kf5windowsystem_harmonyos)
