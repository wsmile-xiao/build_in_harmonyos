# libsigc (libsigc++)

libsigc++ 为标准 C++ 提供类型安全的信号/槽（signal-slot）回调机制：`sigc::signal` 发射信号，
`sigc::slot` 承载任意可调用对象，`sigc::trackable` 在对象析构时自动断开连接，配合
`mem_fun`/`ptr_fun`/`bind` 等适配器使用。它是 glibmm、gtkmm 等 GNOME C++ 绑定的基础依赖。

## 版本

- **2.12.1** (2026-07-19) — Windows 交叉构建验证，状态 built
- **2.10.8** (2026-07-12) — 适配 HarmonyOS PC (aarch64)，状态 built

## 构建系统

meson（官方 tarball 由 `meson dist` 生成，不含 configure 脚本）

## 依赖

无第三方依赖；运行期仅依赖 libc++ 与系统 libc。

## 安装产物

- 头文件：`include/sigc++-2.0/sigc++/`
- 配置头：`lib/sigc++-2.0/include/sigc++config.h`
- 库文件：`lib/libsigc-2.0.so`
- pkg-config：`lib/pkgconfig/sigc++-2.0.pc`

## 许可证

LGPL-2.1-or-later

## 上游

https://github.com/libsigcplusplus/libsigcplusplus
