cmake_minimum_required(VERSION 3.15)
project(test_libexif_gtk C)

# 为什么不用 CMakeDeps 目标链接：
# gtk/3.24.43 配方是"扁平包"（未声明 cpp_info.requires），CMakeDeps 生成的
# 目标只能带出直接依赖的头目录，pango 的公共头 <pango/pango-coverage.h>
# 里 `#include <hb.h>` 所需的 harfbuzz 头目录传不过来 —— 实测报
#   fatal error: 'hb.h' file not found
# 改用 pkg-config 解析完整 Requires 链（libexif-gtk3 → libexif + gtk+-3.0
# → pango → harfbuzz/fribidi ...），与 gtkspell3-3.0 测试包同款先例。
find_package(PkgConfig REQUIRED)
pkg_check_modules(LIBEXIF_GTK3 REQUIRED libexif-gtk3)

# pkg-config 在少数场景会吐出空变量碎片（如 "-I"），过滤不存在的目录
set(LIBEXIF_GTK3_CLEAN_INCLUDE_DIRS)
foreach(inc_dir IN LISTS LIBEXIF_GTK3_INCLUDE_DIRS)
    if(EXISTS "${inc_dir}")
        list(APPEND LIBEXIF_GTK3_CLEAN_INCLUDE_DIRS "${inc_dir}")
    endif()
endforeach()

add_executable(test_libexif_gtk test_libexif_gtk.c)
target_include_directories(test_libexif_gtk PRIVATE ${LIBEXIF_GTK3_CLEAN_INCLUDE_DIRS})
target_link_directories(test_libexif_gtk PRIVATE ${LIBEXIF_GTK3_LIBRARY_DIRS})
target_link_libraries(test_libexif_gtk PRIVATE ${LIBEXIF_GTK3_LIBRARIES})

# dlopen/dlsym 需要 libdl（OHOS 上由 libc 提供，显式列出以便消费端可见）
find_library(DL_LIBRARY NAMES dl)
if(DL_LIBRARY)
    target_link_libraries(test_libexif_gtk PRIVATE ${DL_LIBRARY})
endif()

enable_testing()
add_test(NAME test_libexif_gtk COMMAND test_libexif_gtk)
