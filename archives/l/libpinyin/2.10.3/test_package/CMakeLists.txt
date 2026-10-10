cmake_minimum_required(VERSION 3.15)
project(test_libpinyin C)

find_package(libpinyin CONFIG REQUIRED)
find_package(glib2 CONFIG REQUIRED)
include(${CMAKE_BINARY_DIR}/generators/bdb_vars.cmake)
find_library(GLIB2_LIB NAMES glib-2.0 PATHS "${glib_PACKAGE_FOLDER_RELEASE}/lib"
             NO_DEFAULT_PATH REQUIRED)

set(LIBPINYIN_DATADIR "${libpinyin_PACKAGE_FOLDER_RELEASE}/share/libpinyin/data")
add_executable(test_libpinyin test.c)
target_link_libraries(test_libpinyin PRIVATE libpinyin ${GLIB2_LIB} ${BDB_STATIC_LIB})
target_compile_definitions(test_libpinyin PRIVATE SYSTEM_DATADIR="${LIBPINYIN_DATADIR}")
