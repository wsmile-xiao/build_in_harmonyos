cmake_minimum_required(VERSION 3.15)
project(test_libonvif C)

# Find the packages via Conan-generated CMakeDeps. libxml2 is linked
# explicitly because onvif.h does not include its own libxml2 headers,
# and the CMakeDeps propagation of the libonvif -> libxml2 edge is
# LINK_ONLY (headers are not re-exported by upstream).
find_package(libonvif REQUIRED)
find_package(libxml2 REQUIRED)

add_executable(test_libonvif test_onvif_api.c)
# libxml2's Conan recipe declares the CMake target LibXml2::LibXml2
# (upstream FindLibXml2 naming), not libxml2::libxml2.
target_link_libraries(test_libonvif libonvif::libonvif LibXml2::LibXml2)
# The published libxml2/2.15.3.1 binary bakes an empty cpp_info
# (libxml2_INCLUDE_DIRS_RELEASE is empty in the CMakeDeps data file), and
# its headers are nested under <pkg>/include/libxml2/, so add that dir
# from the CMakeDeps package-folder variable directly.
if(DEFINED libxml2_PACKAGE_FOLDER_RELEASE)
    target_include_directories(test_libonvif PRIVATE "${libxml2_PACKAGE_FOLDER_RELEASE}/include/libxml2")
endif()

enable_testing()
add_test(NAME test_libonvif COMMAND test_libonvif)
