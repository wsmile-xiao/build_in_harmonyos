cmake_minimum_required(VERSION 3.15)
project(test_gsettings_desktop_schemas C)

# Find the package via Conan-generated CMakeDeps
find_package(gsettings-desktop-schemas REQUIRED)

add_executable(test_gsettings_desktop_schemas test.c)
target_link_libraries(test_gsettings_desktop_schemas gsettings-desktop-schemas::gsettings-desktop-schemas)

enable_testing()
add_test(NAME test_gsettings_desktop_schemas COMMAND test_gsettings_desktop_schemas)
