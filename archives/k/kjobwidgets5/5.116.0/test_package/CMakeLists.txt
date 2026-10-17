cmake_minimum_required(VERSION 3.16)
project(test_kjobwidgets5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# NOTE: AUTOMOC is deliberately NOT enabled.  The Qt5 CMake configs shipped
# inside the qt5-qtbase package are consumed through CMakeDeps, which exports
# no Qt5::moc target on this chain, so AUTOMOC would fail at generate time with
# "Could not find moc executable target Qt5::moc".  The test helper below adds
# no signals/slots of its own (connections go through the KJob base class
# meta-object), so no meta-object compilation is required.
find_package(Qt5 5.15.2 REQUIRED COMPONENTS Core Gui Widgets)
find_package(KF5JobWidgets 5.116.0 REQUIRED)

add_executable(test_kjobwidgets5 test.cpp)
target_link_libraries(test_kjobwidgets5 PRIVATE Qt5::Widgets KF5::JobWidgets)

# /proc/self/maps reports the bare soname on OHOS, so give the test the real
# packaged library path to assert its ELF adaptation properties.
target_compile_definitions(test_kjobwidgets5 PRIVATE
    KJOBWIDGETS_SO_PATH="$<TARGET_FILE:KF5::JobWidgets>")

enable_testing()
add_test(NAME test_kjobwidgets5 COMMAND test_kjobwidgets5)
