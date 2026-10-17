cmake_minimum_required(VERSION 3.15)
project(test_kdbusaddons CXX)

# Find the package via Conan-generated CMakeDeps
find_package(KF6DBusAddons REQUIRED)

# Consumer test: construct KDBusService and query the D-Bus service name.
add_executable(test_kdbusaddons test_kdbusaddons.cpp)
target_link_libraries(test_kdbusaddons KF6::DBusAddons Qt6::Core Qt6::DBus)

# HarmonyOS-specific test asserting the OHOS adaptation path: no X11
# (WITH_X11=OFF, Qt6Gui/Qt6GuiPrivate not linked) and graceful degradation
# when no D-Bus session bus is present (NoExitOnFailure, isRegistered()==false).
add_executable(test_kdbusaddons_ohos test_kdbusaddons_ohos.cpp)
target_link_libraries(test_kdbusaddons_ohos KF6::DBusAddons Qt6::Core Qt6::DBus)

enable_testing()
add_test(NAME test_kdbusaddons COMMAND test_kdbusaddons)
add_test(NAME test_kdbusaddons_ohos COMMAND test_kdbusaddons_ohos)
