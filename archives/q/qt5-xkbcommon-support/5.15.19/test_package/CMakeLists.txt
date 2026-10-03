cmake_minimum_required(VERSION 3.16)
project(test_qt5_xkbcommon_support CXX)

# Real consumer configuration: the point of this package is that a CMake project
# can find the Qt5XkbCommonSupport module and link its private target, exactly
# like kwayland5/5.116.0 does.
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt5XkbCommonSupport REQUIRED)

if(NOT TARGET Qt5::XkbCommonSupportPrivate)
    message(FATAL_ERROR "Qt5::XkbCommonSupportPrivate target was not created by find_package")
endif()

get_target_property(_xkbsup_location Qt5::XkbCommonSupportPrivate IMPORTED_LOCATION)
if(NOT _xkbsup_location OR NOT EXISTS "${_xkbsup_location}")
    message(FATAL_ERROR "imported archive missing: ${_xkbsup_location}")
endif()
message(STATUS "FIND_PACKAGE_OK Qt5::XkbCommonSupportPrivate=${_xkbsup_location}")

add_executable(test_xkbsupport src/test_xkbsupport.cpp)
target_link_libraries(test_xkbsupport PRIVATE Qt5::XkbCommonSupportPrivate)

# The static archive needs the Qt5 shared libraries at link time; the module's
# CMake config deliberately does not hard-code Qt's own paths (the conan qt
# package owns them), so bind them here through the Qt5 Gui target that
# Qt5XkbCommonSupportConfig.cmake's include roots belong to.
find_package(Qt5Gui QUIET)
if(TARGET Qt5::Gui)
    target_link_libraries(test_xkbsupport PRIVATE Qt5::Gui Qt5::Core)
endif()

enable_testing()
add_test(NAME xkbsupport_api COMMAND test_xkbsupport)

# --- end-to-end consumer flow (rule-12 Hongmeng-specific test) ---------------
#
# A complete consumer use case rather than an assertion list: a full simulated
# typing session driven through the module's own translation path (lookupString
# for text, keysymToQtKey/modifiers for the Qt key), with the produced text
# compared character for character. See e2e/xkbcommon_e2e.cpp.
add_executable(xkbcommon_e2e e2e/xkbcommon_e2e.cpp)
target_link_libraries(xkbcommon_e2e PRIVATE Qt5::XkbCommonSupportPrivate)
if(TARGET Qt5::Gui)
    target_link_libraries(xkbcommon_e2e PRIVATE Qt5::Gui Qt5::Core)
endif()

add_test(NAME xkbcommon_typing_e2e COMMAND xkbcommon_e2e)
