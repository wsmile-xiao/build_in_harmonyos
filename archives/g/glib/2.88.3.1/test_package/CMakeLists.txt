cmake_minimum_required(VERSION 3.15)
project(test_glib2 C)

find_package(glib2 CONFIG REQUIRED)

add_executable(test_glib2 test_glib.c)
add_executable(test_glib2_loader test_loader.c)
target_link_libraries(test_glib2_loader PRIVATE ${CMAKE_DL_LIBS})
if(NOT DEFINED GLIB2_TEST_RPATH_LINK_OPTION OR
   GLIB2_TEST_RPATH_LINK_OPTION STREQUAL "")
  message(FATAL_ERROR "missing GLib consumer RPATH link option")
endif()
target_link_options(test_glib2 PRIVATE "${GLIB2_TEST_RPATH_LINK_OPTION}")
target_link_libraries(test_glib2 PRIVATE
  glib2::gio
  glib2::girepository
  glib2::gmodule
  glib2::gthread
)
