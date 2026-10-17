# =============================================================================
# qt-config.cmake — adapter that lets find_package(sensorfw) work under CMakeDeps
# =============================================================================
#
# WHY THIS FILE EXISTS
# --------------------
# `qt` is a direct requirement of sensorfw, so CMakeDeps writes into the
# generated `sensorfw-config.cmake`:
#
#     foreach(_DEPENDENCY ${sensorfw_FIND_DEPENDENCY_NAMES} )
#         if(NOT ${_DEPENDENCY}_FOUND)
#             find_dependency(${_DEPENDENCY} REQUIRED ${${_DEPENDENCY}_FIND_MODE})
#         endif()
#     endforeach()
#
# with `sensorfw_FIND_DEPENDENCY_NAMES = qt`.  (Verified: CMakeDeps collects the
# consumer-visible subset of the package's *direct* requirements and does not
# filter it by find mode; `transitive_headers`/`transitive_libs` make no
# difference to this list - two throwaway packages that were byte-identical
# apart from those flags produced byte-identical CMakeDeps output.)
#
# The `qt` Conan package, however, deliberately ships NO CMakeDeps config:
#
#     qt/5.15.19.1: package_info()
#         self.cpp_info.set_property("cmake_find_mode", "none")
#         self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
#
# because it provides the real, relocatable Qt5<Module>Config.cmake set itself.
# Nothing named `qt-config.cmake` / `qtConfig.cmake` can therefore ever exist,
# and every CMakeDeps consumer of sensorfw would fail with
#
#     Could not find a package configuration file provided by "qt"
#
# (observed verbatim in the first `conan create` of this package).
#
# Mapping the dependency's CMake file name onto `Qt5` - the technique used by
# archives/a/attica5/5.116.0 and archives/l/libaccounts-qt/1.13 - does NOT work
# here: that only changes the call to `find_dependency(Qt5 ...)`, and
# Qt5Config.cmake hard-refuses to be found without components:
#
#     if (NOT Qt5_FIND_COMPONENTS)
#         set(Qt5_NOT_FOUND_MESSAGE "The Qt5 package requires at least one component")
#         set(Qt5_FOUND False)
#         return()
#     endif()
#
# while the CMakeDeps template cannot pass components through find_dependency().
#
# So the two names are bridged here instead.  This directory is prepended to
# CMAKE_PREFIX_PATH by test_package/CMakeLists.txt before find_package(sensorfw),
# which makes the generated `find_dependency(qt REQUIRED)` load this file.
#
# WHAT IT DOES
# ------------
#   1. finds the real Qt5 through the qt package's own relocatable config tree
#      (the caller must have `<qt package>/lib/cmake` on CMAKE_PREFIX_PATH);
#   2. defines the umbrella target `qt::qt` that the generated sensorfw target
#      files reference.  (Note: that reference lives in sensorfw_DEPS_TARGET and
#      is only forwarded to sensorfw::sensorfw when the package declares no
#      cpp_info.libs; sensorfw does declare libs, so this is belt-and-braces.)
#
# It is deliberately kept in test_package/ as the canonical consumer example:
# a downstream CMakeDeps consumer of sensorfw needs the same bridge, which is
# documented in archives/s/sensorfw/0.15.2/notes.md.
# =============================================================================

if(NOT TARGET Qt5::Core)
    include(CMakeFindDependencyMacro)
    find_dependency(Qt5 5.15 REQUIRED COMPONENTS Core DBus)
endif()

if(NOT TARGET qt::qt)
    add_library(qt::qt INTERFACE IMPORTED)
    set_property(TARGET qt::qt PROPERTY INTERFACE_LINK_LIBRARIES "Qt5::Core;Qt5::DBus")
endif()
