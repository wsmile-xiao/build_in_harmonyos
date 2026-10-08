cmake_minimum_required(VERSION 3.15)
project(wmfire_harmony_consumer C)

# wmfire 是应用包（package_type="application"）：消费它的人不会继承其依赖的
# headers/libs，所以这里直接声明并链接 wmfire 运行期真正调用的两个库——
# libX11（-g 几何参数解析）与 libgtop（火焰动画用的 CPU 计数器）。

# libX11：走正常的 CMakeDeps 目标。
find_package(libx11 CONFIG REQUIRED)

# glib：提供 libgtop 公共头的依赖（glibtop.h -> glib.h）以及下面用到的
# -lintl（glib 包内自带 libintl.so），走正常的 CMakeDeps 组件目标。
find_package(GLib CONFIG REQUIRED)

# libgtop 不能用 find_package(libgtop CONFIG)：
# libgtop 的 cpp_info.libs 声明为 ["gtop-2.0", "intl"]，而 libintl.so 由 glib 包
# 提供、并不在 libgtop 包自己的 lib/ 里（知识库 E508）。CMakeDeps 的
# conan_package_library_targets() 只在本包的 libdir 内
# find_library(... NO_DEFAULT_PATH)，找不到 'intl' 就直接
# message(FATAL_ERROR "Library 'intl' not found in package ...")，
# 因此任何消费者只要 find_package(libgtop CONFIG) 都会在 configure 阶段失败。
# 这里改为直接使用 conanfile.py 从依赖 cpp_info 里取出的静态库实体路径。
add_library(hc_libgtop STATIC IMPORTED)
set_target_properties(hc_libgtop PROPERTIES
    IMPORTED_LOCATION "${HC_LIBGTOP_ARCHIVE}"
    INTERFACE_INCLUDE_DIRECTORIES "${HC_LIBGTOP_INCLUDE_DIRS}")

add_executable(hc_consumer src/hc_consumer.c)
target_link_libraries(hc_consumer PRIVATE
    hc_libgtop      # libgtop-2.0.a（静态库）
    intl            # g_libintl_ngettext，来自 glib 包的 libintl.so
    GLib::GLib
    libx11::libx11
)
