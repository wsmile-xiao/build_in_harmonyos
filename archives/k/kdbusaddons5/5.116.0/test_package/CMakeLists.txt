cmake_minimum_required(VERSION 3.16)
project(test_kdbusaddons5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Qt5 5.15.2 REQUIRED COMPONENTS Core DBus)
find_package(KF5DBusAddons 5.116.0 REQUIRED)

# The KF5DBusAddons config exposes KF5::DBusAddons (target name normalized by
# the project's own KF5DBusAddonsConfig.cmake).  Link it via the KF5 alias.
add_executable(test_kdbusaddons5 test.cpp)
target_link_libraries(test_kdbusaddons5
    PRIVATE Qt5::Core Qt5::DBus KF5::DBusAddons)

enable_testing()
add_test(NAME test_kdbusaddons5 COMMAND test_kdbusaddons5)
