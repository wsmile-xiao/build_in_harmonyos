cmake_minimum_required(VERSION 3.16)
project(mock_datamanagement_server C)

# 头/库路径由 conanfile._build_mock_server() 经 extra_defs 注入（glib 包 +
# 全部依赖包 lib 目录；glib 为静态包，其传递依赖 pcre2/z/ffi/intl 一并静态链接）
add_executable(mock_datamanagement_server mock_datamanagement_server.c)
target_include_directories(mock_datamanagement_server PRIVATE ${GLIB_INCLUDE_DIRS})
target_link_directories(mock_datamanagement_server PRIVATE ${GLIB_LIBRARY_DIRS})
target_link_libraries(mock_datamanagement_server PRIVATE
    gio-2.0 glib-2.0 gobject-2.0 gmodule-2.0
    pcre2-8 z ffi intl)
# OHOS conan toolchain 链可执行文件带 --no-undefined；glib 传递依赖在
# 制品仓为静态库、sysroot 部分无链接库（运行时由系统加载路径解析）→
# 放行共享库未定义符号（防御，静态链接已覆盖主体）。
target_link_options(mock_datamanagement_server PRIVATE -Wl,--allow-shlib-undefined)
