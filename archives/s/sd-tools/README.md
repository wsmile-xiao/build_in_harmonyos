# sd-tools

sd-tools 是 systemd 项目的一部分，提供了 sysusers 和 tmpfiles 工具。

## 软件信息

- **版本**: 0.99.0
- **构建系统**: meson
- **编译器**: clang/clang++
- **主页**: https://github.com/systemd/systemd

## 功能

### sd-sysusers
用户/组管理工具，用于创建系统用户和组。

### sd-tmpfiles
临时文件管理工具，用于创建、删除和清理临时文件和目录。

## 依赖

- libcap 2.69（运行时依赖）

## musl libc 兼容性

sd-tools 依赖 glibc 特有的扩展函数，在 OHOS/musl libc 上需要额外的适配：

- fgetpwent/fgetgrent: musl 不支持，已实现替代版本
- putpwent/putgrent/putspent: musl 不支持，已实现替代版本
- reallocarray: BSD 扩展，musl 不支持，已实现替代版本
- secure_getenv: glibc 扩展，已映射为 getenv
- program_invocation_short_name: glibc 扩展，已定义为常量

## 编译选项

- `-Dtests=false`: 禁用测试
- `-Dacl=disabled`: 禁用 ACL 支持（musl 不支持）

## 已编译版本

- 0.99.0 (2026-06-08)