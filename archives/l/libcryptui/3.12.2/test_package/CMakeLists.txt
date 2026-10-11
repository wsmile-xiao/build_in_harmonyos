cmake_minimum_required(VERSION 3.15)
project(test_libcryptui C)

# PkgConfigDeps 而非 CMakeDeps：gtk/3.24.43 等扁平配方未声明 cpp_info.requires，
# CMakeDeps 无法把 pango/harfbuzz 等传递头文件传播给消费者；pkg_check_modules
# 让 pkg-config 解析 cryptui-0.0.pc 的完整 Requires 链
# （gtk+-3.0 gio-2.0 dbus-glib-1），同时验证被测包安装的 .pc 文件本身。
find_package(PkgConfig REQUIRED)
pkg_check_modules(CRYPTUI REQUIRED IMPORTED_TARGET cryptui-0.0)

add_executable(test_libcryptui test_libcryptui.c)

# cryptui.h 用 #error 强制消费者声明 API 稳定性认知（上游要求，见
# cryptui.h:27-29）；conan 侧同时通过 cpp_info.defines 提供给 CMakeDeps 消费者，
# 此处按上游 .pc 语义（.pc 不携带该宏）由消费者自行定义。
target_compile_definitions(test_libcryptui PRIVATE LIBCRYPTUI_API_SUBJECT_TO_CHANGE)

target_link_libraries(test_libcryptui PRIVATE PkgConfig::CRYPTUI)

set_property(TARGET test_libcryptui PROPERTY C_STANDARD 99)
