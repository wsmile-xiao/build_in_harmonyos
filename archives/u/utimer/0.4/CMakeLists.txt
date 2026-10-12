cmake_minimum_required(VERSION 3.15)
project(utimer VERSION 0.4 LANGUAGES C)
include(GNUInstallDirs)
find_package(glib2 CONFIG REQUIRED)
find_package(proxy-libintl CONFIG REQUIRED)
# Same complete production source list and unchanged registered test driver
# as upstream src/Makefile.am and src/tests/Makefile.am.
add_library(utimer-core OBJECT src/timer.c src/utils.c src/log.c globals.c)
target_include_directories(utimer-core PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src")
target_compile_features(utimer-core PRIVATE c_std_99)
target_link_libraries(utimer-core PUBLIC glib2::glib glib2::gobject glib2::gthread glib2::gio proxy-libintl::intl)
target_compile_definitions(utimer-core PUBLIC
  PACKAGE="utimer" PACKAGE_STRING="utimer\ 0.4" GETTEXT_PACKAGE="utimer"
  LOCALEDIR="${CMAKE_INSTALL_FULL_LOCALEDIR}")
add_executable(utimer src/utimer.c)
target_link_libraries(utimer PRIVATE utimer-core)
add_executable(utimer-upstream-tests src/tests/maintests.c)
target_link_libraries(utimer-upstream-tests PRIVATE utimer-core)
install(TARGETS utimer RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}")
# The official release has no PO catalogs (po/LINGUAS is empty); gettext
# remains linked through GLib's proxy-libintl dependency, not stubbed out.
