cmake_minimum_required(VERSION 3.16)
project(test_kimageformats5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Qt5 5.15.2 REQUIRED COMPONENTS Core Gui)

# kimageformats5 is a plugin package: verify the image format plugins were
# installed into the package's plugins/imageformats folder. The package root
# is passed by the recipe through the KIMAGEFORMATS5_ROOT toolchain variable.
if(NOT DEFINED KIMAGEFORMATS5_ROOT)
    message(FATAL_ERROR "KIMAGEFORMATS5_ROOT not set by the Conan toolchain")
endif()

# The plugin set follows the recipe options (with_openexr/with_libraw); the
# unconditional core plugins are always expected, the optional ones are
# only checked when the corresponding directory entry exists.
set(CORE_PLUGINS
    kimg_ani kimg_hdr kimg_pcx kimg_pic kimg_psd kimg_qoi
    kimg_ras kimg_rgb kimg_tga kimg_xcf)

foreach(plugin IN LISTS CORE_PLUGINS)
    set(plugin_path "${KIMAGEFORMATS5_ROOT}/plugins/imageformats/${plugin}.so")
    if(NOT EXISTS "${plugin_path}")
        message(FATAL_ERROR "missing core image format plugin: ${plugin_path}")
    endif()
endforeach()

set(plugin_dir "${KIMAGEFORMATS5_ROOT}/plugins/imageformats")
file(GLOB installed_plugins "${plugin_dir}/kimg_*.so")
list(LENGTH installed_plugins plugin_count)
if(plugin_count LESS 10)
    message(FATAL_ERROR "expected at least 10 kimg_*.so plugins, found ${plugin_count} in ${plugin_dir}")
endif()

# Compile-time link check: the consumer links against Qt5::Gui which loads
# the plugins at runtime through the plugin path set by the test binary.
add_executable(test_kimageformats5 test_kimageformats5.cpp)
target_link_libraries(test_kimageformats5 PRIVATE Qt5::Core Qt5::Gui)

enable_testing()
add_test(NAME test_kimageformats5
         COMMAND test_kimageformats5)
# Qt5 appends the "imageformats" subdirectory to every library path, so the
# environment must point at the parent "plugins" directory of the package.
set_tests_properties(test_kimageformats5 PROPERTIES
    ENVIRONMENT "KIMAGEFORMATS5_PLUGIN_DIR=${KIMAGEFORMATS5_ROOT}/plugins")
