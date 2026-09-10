# libpciaccess 0.19 适配笔记

## 编译环境

- 构建系统：Meson 1.11.1 / Ninja 1.13.1
- 编译日期：2026-09-09
- 编译器：Clang 15.0.4
- 架构：HarmonyOS PC arm64
- 状态：built

## 编译步骤

探索阶段使用官方源码包，配置并构建：

```bash
meson setup builddir --prefix=/storage/Users/currentUser/usr/local \
  -Dinstall-scanpci=true -Dlinux-rom-fallback=false
meson compile -C builddir -j2
meson test -C builddir --print-errorlogs
DESTDIR=/storage/Users/currentUser/builds/libpciaccess-0.19.test \
  meson install -C builddir
```

Conan 配方使用 MesonToolchain，依赖 `zlib/1.3.1`，默认构建静态库，并关闭 `scanpci` 安装。

## 上游测试清点

对官方 `libpciaccess-0.19.tar.xz` 完整清点：

| 清点项 | 数量 | 证据 |
|--------|-----:|------|
| 名称包含 test 的目录 | 0 | `find . -type d -iname '*test*'` 无输出 |
| 名称包含 test 的文件 | 0 | `find . -type f -iname '*test*'` 无输出 |
| Meson `test()` 注册 | 0 | 对全部 4 个 `meson.build`（根目录、`src/`、`scanpci/`、`man/`）搜索 `test(` 无匹配 |
| `meson test` 注册用例 | 0 | 实际输出 `No tests defined.` |

因此上游测试总数为 0，不存在未执行、删除或修改的上游测试。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接时报 `undefined symbol: pci_system_linux_sysfs_create` | Meson 的 `host_machine.system()` 在 HarmonyOS 返回 `harmonyos`，未进入仅匹配 `linux` 的后端源文件分支 | 按知识库 E090，将 `src/meson.build` 的 Linux 条件扩展为同时接受 `linux` 和 `harmonyos` |
| 2 | 消费者初始化返回 13 | 当前沙箱不允许访问 PCI sysfs | 消费者测试仅接受 EACCES、ENOENT、ENOSYS 三种受限环境结果，其他错误仍失败 |
| 3 | CI Meson 报 `Unknown linker(s): [['llvm-ar']]` | CI worker 的 profile 仅声明 clang 绝对路径，Meson 生成的归档器为裸 `llvm-ar`，该进程 PATH 中无法解析 | 从 Conan `tools.build:compiler_executables` 获取 clang 路径，并向 Meson native 文件注入同目录的绝对 `llvm-ar`/`llvm-ranlib` |

## 源码修改

- `0001-meson-treat-harmonyos-as-linux.patch`：在 Meson 平台选择中为 HarmonyOS 启用 Linux sysfs 后端；未引入平台宏或空实现。

## 依赖版本

- `zlib/1.3.1`：已通过 `conan download zlib/1.3.1 -r=ohpcd --only-recipe` 确认制品仓配方存在。

## 验证结果

- 探索构建：通过
- 探索安装：通过
- 上游测试：0/0；命令已执行，输出 `No tests defined.`
- 消费者测试：2/2 通过

详细数据见 `reports/test-report.md`。

## 注意事项

上游提供 `scanpci` 工具，但本次 Conan 包定位为库包并设置 `install-scanpci=false`，不交付命令行工具，因此无需软件级 `commands.json`。
---

**编译结束**: 2026-09-09 02:37
**最终状态**: built
