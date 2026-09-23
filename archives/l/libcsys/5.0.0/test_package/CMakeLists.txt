cmake_minimum_required(VERSION 3.16)
project(test_libcsys CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# libcsys is packaged with cmake_find_mode=none and installs no Config.cmake,
# so it is consumed through the paths injected by test_package/conanfile.py.
# Qt6 comes from the real Qt6Config.cmake chain of qtbase-sql-dbus.
find_package(Qt6 REQUIRED COMPONENTS Core Network DBus)

add_executable(test_libcsys test_libcsys.cpp)
target_include_directories(test_libcsys PRIVATE "${CSYS_INCLUDE_DIR}")
target_link_libraries(
    test_libcsys
    PRIVATE "${CSYS_LIBRARY}" Qt6::Core Qt6::Network Qt6::DBus
)

enable_testing()
add_test(NAME test_libcsys COMMAND test_libcsys)
