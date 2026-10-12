cmake_minimum_required(VERSION 3.15)
project(test_libsignon_qt CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# qtbase on ohpcd ships Qt's own Qt6Config.cmake (cmake_find_mode=none), so
# Qt6 must be found explicitly first: the SignOnQt6 interface links Qt6::Core
# and the library itself needs Qt6::DBus. Qt6_DIR comes from the toolchain.
find_package(Qt6 COMPONENTS Core DBus CONFIG REQUIRED)
find_package(SignOnQt6 REQUIRED)

add_executable(test_libsignon_qt test_libsignon_qt.cpp)

target_link_libraries(test_libsignon_qt
    SignOnQt6::SignOnQt6
    Qt6::DBus
)

enable_testing()
add_test(NAME test_libsignon_qt COMMAND test_libsignon_qt)
