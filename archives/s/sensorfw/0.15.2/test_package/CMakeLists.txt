cmake_minimum_required(VERSION 3.16)
project(test_sensorfw LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ---------------------------------------------------------------------------
# Qt5
# ---------------------------------------------------------------------------
# qt/5.15.19.1 sets the cpp_info property `cmake_find_mode` to "none": the
# recipe ships a complete, relocatable Qt5<Module>Config.cmake tree under
# <qt>/lib/cmake and therefore asks CMakeDeps NOT to generate a replacement
# config for the qt node.  Qt5 has to be found through that directory, which
# test_package/conanfile.py passes in.
if(NOT DEFINED SENSORFW_QT_CMAKE_DIR)
  message(FATAL_ERROR
          "SENSORFW_QT_CMAKE_DIR is not set - configure with "
          "-DSENSORFW_QT_CMAKE_DIR=<qt package>/lib/cmake")
endif()
list(PREPEND CMAKE_PREFIX_PATH "${SENSORFW_QT_CMAKE_DIR}")

# Core: QCoreApplication / QObject / QVariant / QMetaObject
# DBus: <QDBusArgument>, pulled in by datatypes/xyz.h
find_package(Qt5 5.15 COMPONENTS Core DBus REQUIRED)

# ---------------------------------------------------------------------------
# Bridge for `find_dependency(qt)`
# ---------------------------------------------------------------------------
# `qt` is one of sensorfw's direct requirements, so the CMakeDeps-generated
# sensorfw-config.cmake unconditionally calls `find_dependency(qt ...)` - and
# that cannot resolve, because the qt package deliberately provides no
# CMakeDeps config (see cmake/qt-config.cmake in this directory for the full
# evidence trail).  Prepending this directory to CMAKE_PREFIX_PATH lets that
# call load our bridge, which forwards to the real Qt5 found just above and
# defines the umbrella target `qt::qt` referenced by the generated sensorfw
# target files.
#
# This MUST come before find_package(sensorfw).
list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")

# ---------------------------------------------------------------------------
# The package under test, located through the CMakeDeps-generated
# sensorfw-config.cmake (default file name = package name; target sensorfw::sensorfw).
# The link line is exactly the consumer-side one declared by package_info():
#   -lsensorclient-qt5 -lsensordatatypes-qt5
# ---------------------------------------------------------------------------
find_package(sensorfw REQUIRED)

add_executable(test_sensorfw test_sensorfw.cpp)
target_link_libraries(test_sensorfw PRIVATE
    sensorfw::sensorfw
    Qt5::Core
    Qt5::DBus
)

# NOTE: deliberately NO add_test()/enable_testing() here.
# The consumer run needs a shell wrapper for two platform reasons - the loader
# refuses the Qt package's versioned .so symlinks (test.sh deref-copies the
# DT_NEEDED closure), and the test binary takes the packaged plugin directory
# as argv[1] - so a bare `ctest` entry would register a test that cannot pass.
# The single entry point is test_package/test.sh, invoked from conanfile.py.
