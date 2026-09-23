# libsigc-2 (libsigc++)

libsigc++ 的任务命名包装：上游项目名为 `libsigc++`，本归档按平台任务
命名约定使用 `libsigc-2`（目录与 Conan 包名一致）。

- Conan 引用：`libsigc-2/<版本>`
- 上游：https://github.com/libsigcplusplus/libsigcplusplus
- 名称映射：
  - 上游项目/发布名：`libsigc++`
  - 库文件：`libsigc-2.0.so`（SONAME `libsigc-2.0.so.0`）
  - pkg-config 模块：`sigc++-2.0`
  - CMake 目标：`libsigc-2::libsigc-2`，文件名 `libsigc-2`
- C++ 类型安全的信号/槽（signal-slot）回调库，glibmm / gtkmm 等
  GNOME C++ 绑定的基础依赖
- 纯 C++ 库，零补丁，运行期仅依赖 libc++ 与系统 libc

历史版本（包名 `libsigc`，见 ../libsigc/）：
- 2.10.8（built, 2026-07-12）
- 2.12.1（built, 2026-07-19）
