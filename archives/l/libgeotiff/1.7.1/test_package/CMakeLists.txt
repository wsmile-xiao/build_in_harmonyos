cmake_minimum_required(VERSION 3.15)
project(test_geotiff C)

# Find packages via Conan-generated CMakeDeps
find_package(GeoTIFF REQUIRED)
find_package(TIFF REQUIRED)

add_executable(test_geotiff test_geo.c)
target_link_libraries(test_geotiff GeoTIFF::geotiff)

# TIFF package's cpp_info doesn't set libs/includes, link manually
if(DEFINED libtiff_PACKAGE_FOLDER_RELEASE)
    set(TIFF_PKG_FOLDER "${libtiff_PACKAGE_FOLDER_RELEASE}")
elseif(DEFINED libtiff_PACKAGE_FOLDER_DEBUG)
    set(TIFF_PKG_FOLDER "${libtiff_PACKAGE_FOLDER_DEBUG}")
endif()
if(DEFINED TIFF_PKG_FOLDER)
    target_include_directories(test_geotiff PRIVATE "${TIFF_PKG_FOLDER}/include")
    find_library(TIFF_LIB_PATH tiff PATHS "${TIFF_PKG_FOLDER}/lib" NO_DEFAULT_PATH)
    if(TIFF_LIB_PATH)
        target_link_libraries(test_geotiff ${TIFF_LIB_PATH})
    endif()
endif()

enable_testing()
add_test(NAME test_geotiff COMMAND test_geotiff)
