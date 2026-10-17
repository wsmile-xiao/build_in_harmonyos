cmake_minimum_required(VERSION 3.16)
project(test_kcrash5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# NOTE: AUTOMOC is deliberately NOT enabled — the test has no QObject of its
# own, and on this chain CMakeDeps exports no Qt5::moc target (kjobwidgets5
# precedent), so enabling AUTOMOC would fail at generate time.
#
# KF5Crash is consumed through the config file the package itself installs
# (lib/cmake/KF5Crash, cmake_find_mode=none); the Conan toolchain puts every
# dependency's lib/cmake directory on CMAKE_PREFIX_PATH.  KF5CrashConfig.cmake
# in a shared build only find_dependency()s Qt5Core.
find_package(Qt5 5.15.2 REQUIRED COMPONENTS Core)
find_package(KF5Crash 5.116.0 REQUIRED)

add_executable(test_kcrash5 test.cpp)
target_link_libraries(test_kcrash5 PRIVATE KF5::Crash Qt5::Core)

enable_testing()
add_test(NAME test_kcrash5 COMMAND test_kcrash5)
