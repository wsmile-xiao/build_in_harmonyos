cmake_minimum_required(VERSION 3.15)
project(test_libfm-qt CXX)

# lxqt2-build-tools ships only CMake find-modules and its recipe declares
# cmake_find_mode="none", so CMakeDeps never creates its config/target, yet
# libfm-qt_DEPS_TARGET still references lxqt2-build-tools::lxqt2-build-tools.
# Provide a no-op imported target before find_package(libfm-qt) so the link
# interface resolves.
if(NOT TARGET lxqt2-build-tools::lxqt2-build-tools)
    add_library(lxqt2-build-tools::lxqt2-build-tools INTERFACE IMPORTED)
endif()

# Find the package via Conan-generated CMakeDeps
find_package(libfm-qt REQUIRED)
# libfm-qt public headers include <glib.h>/<gio/gio.h> (folder.h, gobjectptr.h);
# the glib CMakeDeps target does not cover gio-unix-2.0, so add the injected
# GLIB include dirs to every test target.
if(GLIB_INCLUDE_DIRS)
    include_directories(${GLIB_INCLUDE_DIRS})
endif()
find_package(glib REQUIRED)
find_package(Qt6 REQUIRED COMPONENTS Widgets)

# Upstream test: Folder
add_executable(test-folder test-folder.cpp)
target_compile_definitions(test-folder PRIVATE QT_NO_KEYWORDS)
target_link_libraries(test-folder libfm-qt::libfm-qt Qt6::Widgets glib::glib)

# Upstream test: FileDialog
add_executable(test-filedialog test-filedialog.cpp)
target_compile_definitions(test-filedialog PRIVATE QT_NO_KEYWORDS)
target_link_libraries(test-filedialog libfm-qt::libfm-qt Qt6::Widgets glib::glib)

# Upstream test: FolderView
add_executable(test-folderview test-folderview.cpp)
target_compile_definitions(test-folderview PRIVATE QT_NO_KEYWORDS)
target_link_libraries(test-folderview libfm-qt::libfm-qt Qt6::Widgets glib::glib)

# Upstream test: PlacesView
add_executable(test-placesview test-placesview.cpp)
target_compile_definitions(test-placesview PRIVATE QT_NO_KEYWORDS)
target_link_libraries(test-placesview libfm-qt::libfm-qt Qt6::Widgets glib::glib)

# Upstream test: VolumeManager
add_executable(test-volumemanager test-volumemanager.cpp)
target_compile_definitions(test-volumemanager PRIVATE QT_NO_KEYWORDS)
target_link_libraries(test-volumemanager libfm-qt::libfm-qt Qt6::Widgets glib::glib)

# Our test_package test (C++ — libfm-qt is a C++/Qt library, so the file
# must be named .cpp or compiled with the CXX language explicitly)
add_executable(test_libfm-qt test.cpp)
target_compile_definitions(test_libfm-qt PRIVATE QT_NO_KEYWORDS)
target_link_libraries(test_libfm-qt libfm-qt::libfm-qt Qt6::Widgets glib::glib)

enable_testing()
add_test(NAME test-folder COMMAND test-folder)
add_test(NAME test-filedialog COMMAND test-filedialog)
add_test(NAME test-folderview COMMAND test-folderview)
add_test(NAME test-placesview COMMAND test-placesview)
add_test(NAME test-volumemanager COMMAND test-volumemanager)
add_test(NAME test_libfm-qt COMMAND test_libfm-qt)