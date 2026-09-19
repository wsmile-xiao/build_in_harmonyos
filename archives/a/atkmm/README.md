# atkmm

ATK 无障碍工具包的官方 C++ 绑定（GNOME gtk 链 mm 系）。

- 上游：https://gitlab.gnome.org/GNOME/atkmm
- 许可：LGPL-2.1-or-later
- 构建：meson（tarball 预生成绑定，maintainer-mode=false）
- ABI：atkmm-2.36（libatkmm-2.36.so）
- 依赖：glibmm-2.68（ABI 线）+ atk（sigc++-3.0 经 glibmm 传递）

## 已适配版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.36.4 | recipe | 原生 OHOS aarch64，clang 15，libc++，共享库 |
