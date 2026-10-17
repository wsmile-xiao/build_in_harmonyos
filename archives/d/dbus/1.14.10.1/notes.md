# dbus 1.14.10.1 适配笔记（含 dbus-daemon）

## 背景
gtk 3.24.52 测试环境 2 项上游测试失败（gtk:defaultvalue、a11y:tree-relationships）
根因是 OHOS 无 dbus-daemon（D-Bus session bus 无法建立，GtkMountOperation 的
D-Bus 代理与 AT-SPI 无障碍总线均依赖它）。制品仓 `dbus/1.14.10` 仅打包客户端库
（配方注释：daemon 在 OHOS 交叉编译下链接 expat 失败，跳过 dbus-daemon 构建）。
按 R37 发布 **1.14.10.1**：修复 daemon 链接并打包 bin/dbus-daemon。

## 相对 1.14.10 的变更
- `build()`：在 `cmake.build(target="dbus-1")` 之后追加 `cmake.build(target="dbus-daemon")`
  （expat 2.8.2.1 动态库 + CMake 目标级链接，绕过原整包链接失败）
- `package()`：新增从构建输出（bin/ 或 bus/）复制 dbus-daemon 到包内 bin/，
  找不到时降级警告（仅打包客户端库，不失败）
- 其余（DBUS_BUILD_TESTS/TOOLS/DOC/X11/SYSTEMD/SELINUX/APPARMOR OFF、静态库
  package_type、手动复制打包）沿用 1.14.10

## 构建验证
```bash
conan create archives/d/dbus/1.14.10.1 --version=1.14.10.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
- 静态库 libdbus-1.a + bin/dbus-daemon 均打包；test_package 验证客户端库可链接
  且 API 可调用（R34）

## 运行期注意（重要）
- OHOS HMDFS **拒绝 unix socket bind** → session bus 不能走默认 unix 地址，
  需以 TCP 启动：`dbus-daemon --session --nofork --address="tcp:host=127.0.0.1,port=55555"`
  并导出 `DBUS_SESSION_BUS_ADDRESS=tcp:host=127.0.0.1,port=55555`
- TCP 绕行可行性（broadwayd 同机制可跑）由 gtk 测试复测环节（任务 7）实测；
  若 TCP 也被平台限制，2 项 dbus 测试保持失败并如实申报
- **关于 commands.json**：包内 bin/dbus-daemon 是 gtk 测试环境的运行时守护进程
  （D-Bus session bus），非面向用户的 CLI 工具，故不创建 commands.json（R38
  的 bin 工具声明仅适用于面向用户的命令行工具）

**编译日期**: 2026-09-08
**状态**: built（本地 W3 验证通过）
