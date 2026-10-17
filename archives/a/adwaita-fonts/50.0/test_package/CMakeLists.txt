cmake_minimum_required(VERSION 3.15)
project(test_adwaita-fonts C)

# Find the package via Conan-generated CMakeDeps
find_package(adwaita-fonts REQUIRED)

add_executable(test_adwaita-fonts test.c)
target_link_libraries(test_adwaita-fonts adwaita-fonts::adwaita-fonts)

enable_testing()
add_test(NAME test_adwaita-fonts COMMAND test_adwaita-fonts)
