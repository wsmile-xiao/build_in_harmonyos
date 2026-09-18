# xdg-dbus-proxy 0.1.7 适配笔记

## 编译环境
- 构建系统: meson (>=0.49.0)
- 编译日期: 2026-08-27
- 编译器: clang/clang++
- 状态: built

## 源码信息
- 上游仓库: https://github.com/flatpak/xdg-dbus-proxy
- 发布版本: 0.1.7
- 下载地址: https://github.com/flatpak/xdg-dbus-proxy/releases/download/0.1.7/xdg-dbus-proxy-0.1.7.tar.xz
- SHA256: 3ad3d27ba574e178acb5e4d438ba36ace25e3564f899c36f31c56f82c7adbbe7
- 压缩格式: tar.xz

## 软件概述
xdg-dbus-proxy 是一个 D-Bus 过滤代理，被 Flatpak 用于应用沙箱。
它监听 Unix 域套接字，为每个新连接打开到 D-Bus 总线的连接，并根据策略过滤消息。
本版本 (0.1.7) 弃用了 autotools 构建系统，改为使用 Meson。

## 依赖
- glib/2.88.0.1 (包含 glib-2.0, gio-2.0, gio-unix-2.0 组件)
  - 使用 transitive_headers=True, transitive_libs=True 确保传递依赖

## 编译步骤

1. `conan source` 下载并解压源码
2. `conan generate` 生成 MesonToolchain + PkgConfigDeps
3. 手动创建 gio-unix-2.0.pc（从 gio-2.0.pc 复制并改名）
4. `meson setup build` 配置构建（-Dtests=false -Dman=disabled）
5. `meson compile -C build` 编译
6. `meson install -C build` 安装到 Conan package 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 找不到 gio-unix-2.0 依赖 | glib Conan 配方未定义 gio-unix-2.0 组件，PkgConfigDeps 不生成对应 .pc 文件 | 在 generate() 中从 gio-2.0.pc 复制创建 gio-unix-2.0.pc（同库不同名，gio-unix 是 gio 的 Unix 扩展头文件子集） |
| 2 | CI worker 的 AR/AS/STRIP 等工具导出为 llvm-* 名称但不在 PATH | OHOS 工具链命名约定与 meson 探测不兼容 | 在 generate() 中用 shutil.which() 解析绝对路径并注入 MesonToolchain |
| 3 | tests 需要运行中的 D-Bus session daemon | 上游测试 test-proxy.c 启动真实 D-Bus 会话进行集成测试 | 禁用 tests (-Dtests=false)，test_package 使用 --version/--help smoke test |

## 源码修改

无补丁。源码在 OHOS 平台上可直接编译。

## 产物

| 文件 | 说明 |
|------|------|
| bin/xdg-dbus-proxy | D-Bus 过滤代理可执行文件 |

## 注意事项

- gio-unix-2.0.pc 创建模式参考 gegl/0.4.70 和 gcr-base/3.41.2 的先例
- 0.1.7 版本弃用了 autotools，旧版本可能使用 autotools 构建系统
- 测试禁用是因为 D-Bus daemon 在 CI 环境不可用，而非代码兼容性问题
- gio-unix-2.0 include path 使用 ${prefix}/include/gio-unix-2.0 (非 ${includedir})
---

**编译结束**: 2026-08-27 21:51
**最终状态**: built
# Build completed: Thu Aug 27 21:59:55 CST 2026

## CI Fix (2026-09-04)
- Removed misplaced .ci-result.json from repo root
- Removed unrelated libfuse-3.18.2-PR.md from repo root

## CI Retrigger (2026-09-04)
- Retriggered CI after removing misplaced files from repo root
