cmake_minimum_required(VERSION 3.15)
project(test_ctpl C)

find_package(ctpl REQUIRED)

add_executable(test_ctpl test.c)
target_link_libraries(test_ctpl ctpl::ctpl)
# Static glib on OHOS needs g_libintl_* from its vendored proxy-libintl;
# the glib CMakeDeps target does not propagate it (zeitgeist precedent).
if(DEFINED GLIB_LIBINTL AND NOT "${GLIB_LIBINTL}" STREQUAL "")
  target_link_libraries(test_ctpl "${GLIB_LIBINTL}")
endif()

enable_testing()
add_test(NAME test_ctpl COMMAND test_ctpl)
