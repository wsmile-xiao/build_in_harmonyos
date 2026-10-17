cmake_minimum_required(VERSION 3.15)
project(test_kodi_platform LANGUAGES CXX)

# Resolve through Conan CMakeDeps, same as any downstream Kodi add-on.
# cmake_file_name is "kodiplatform" (matches upstream config-mode file).
find_package(kodiplatform CONFIG REQUIRED)

add_executable(test_kodi_platform test_kodi_platform.cpp)
target_compile_features(test_kodi_platform PRIVATE cxx_std_17)
target_link_libraries(test_kodi_platform PRIVATE kodiplatform::kodiplatform)

enable_testing()
add_test(NAME test_kodi_platform COMMAND test_kodi_platform)
