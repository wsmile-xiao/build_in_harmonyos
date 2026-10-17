cmake_minimum_required(VERSION 3.15)
project(test_libpinyin C)

find_package(libpinyin CONFIG REQUIRED)
find_package(glib2 CONFIG REQUIRED)
include(${CMAKE_BINARY_DIR}/generators/bdb_vars.cmake)
# OHPCD 仓的 glib 包 cpp_info 未发布 libs 名（targets 为纯 INTERFACE），
# 这里直接从其包内 lib 目录定位 libglib-2.0.so 全路径链接。
find_library(GLIB2_LIB NAMES glib-2.0 PATHS "${glib_PACKAGE_FOLDER_RELEASE}/lib"
             NO_DEFAULT_PATH)

# 包内模型数据目录（CMakeDeps 暴露 <pkg>_PACKAGE_FOLDER_<CONFIG>；数据安装路径
# share/libpinyin/data 与上游 CMake 的 PROJECT_VERSION 无关）
set(LIBPINYIN_DATADIR "${libpinyin_PACKAGE_FOLDER_RELEASE}/share/libpinyin/data")
message(STATUS "LIBPINYIN_DATADIR=${LIBPINYIN_DATADIR}")

add_executable(test_libpinyin test.c)
target_link_libraries(test_libpinyin PRIVATE libpinyin ${GLIB2_LIB} ${BDB_STATIC_LIB})
target_compile_definitions(test_libpinyin PRIVATE SYSTEM_DATADIR="${LIBPINYIN_DATADIR}")
