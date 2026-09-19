cmake_minimum_required(VERSION 3.15)
project(test_upower-glib C)

# Find the package via Conan-generated CMakeDeps
find_package(upower-glib REQUIRED)

add_executable(test_upower-glib test.c)
target_link_libraries(test_upower-glib upower-glib::upower-glib)

# HarmonyOS/aarch64 specialty test (enum round-trip, version macros,
# UpClient graceful failure without a D-Bus daemon)
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos upower-glib::upower-glib)

enable_testing()
add_test(NAME test_upower-glib COMMAND test_upower-glib)
add_test(NAME test_ohos COMMAND test_ohos)
