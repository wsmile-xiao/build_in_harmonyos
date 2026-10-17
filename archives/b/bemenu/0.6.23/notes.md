# bemenu 0.6.23 适配笔记

## 编译环境
- 构建系统: GNUmakefile (plain Make, not autotools/cmake/meson)
- 编译日期: 2026-07-06
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

bemenu 使用 GNUmakefile 构建系统，不是 autotools。构建命令：

```bash
source .build-context-bemenu-0.6.23
cd $BUILD_SRC_DIR
make CC=clang clients          # 只构建核心库和客户端二进制
make CC=clang PREFIX=$DEFAULT_PREFIX install-base  # 安装
make CC=clang PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX install-base  # Staging
```

注意：必须设置 `CC=clang`，因为系统没有 `cc` 软链接（E001）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 鸿蒙环境无法直接访问 github.com | 使用 gh-proxy.com 镜像下载 |
| 2 | bemenu --version 无输出 | bm_init() 在 parse_args() 之前调用，无渲染器时返回 false 导致直接退出 | 修改源码：将 parse_args() 移到 bm_init() 之前 |
| 3 | make install 失败 | PREFIX="" 导致安装到 /lib（只读文件系统） | conanfile.py 中改用手动 copy 而非 make install |
| 4 | conan test_package 运行时找不到 libbemenu.so | conanrun env 未正确设置 LD_LIBRARY_PATH | test_package 中直接在命令中设置 LD_LIBRARY_PATH |
| 5 | check-symbols 测试失败 | 需要所有渲染器（curses/x11/wayland）已构建 | 预期失败，OHOS 上无法构建渲染器 |

## 源码修改

### Patch 0001: client/bemenu-run.c
- 将 `parse_args(&client, &argc, &argv)` 从 `bm_init()` 之后移到之前
- 原因：bm_init() 在无渲染器时返回 false，导致 --version/--help 无法工作

### Patch 0002: client/bemenu.c
- 同上修改，应用于 bemenu.c 的 main() 函数

## 依赖版本

- 无 Conan 依赖（bemenu 核心库仅需系统 libc）
- 渲染器依赖（未安装）：ncurses, x11, cairo, pango, wayland-client, xkbcommon

## 验证结果

```bash
$ bemenu --version
bemenu v0.6.23

$ bemenu-run --version
bemenu-run v0.6.23

$ bemenu --help
(完整帮助文本输出)
```

Conan 验证: G0-G4 + L2/L4/L5 全部 PASS

## 可用功能

- ✅ libbemenu.so — 核心菜单库，可链接调用
- ✅ bemenu --version / --help — 版本和帮助信息
- ✅ bemenu-run --version / --help — 版本和帮助信息
- ❌ 菜单显示功能 — 需要 curses/x11/wayland 渲染器（OHOS 上不可用）

## 适配范围（R40 人工确认）

bemenu 属于 R40 定义的「图形/渲染」类库（动态菜单库，依赖 curses/x11/wayland 渲染器）。

当前适配范围：**仅提供 libbemenu.so 的 API 级链接能力**，不涉及实际渲染/菜单显示功能。

已知限制：
- 渲染器（curses/x11/wayland）在 OHOS 上不可用，无法构建
- bm_init() 在无渲染器时返回 false，补丁将 parse_args() 前移以使 --version/--help 可用
- test_package 仅调用 bm_version() 验证 API 链接，无法验证菜单显示功能
- 如需在 OHOS 上实现菜单显示，需开发 OHOS 原生渲染器（如 ArkUI 后端）

## 注意事项

- bemenu 不是 autotools 项目，使用 GNUmakefile。conanfile.py 使用 `self.run("make ...")` 而非 Autotools 工具链
- 构建时必须设置 `CC=clang`（系统无 cc 软链接）
- 渲染器（curses/x11/wayland）在 OHOS 上不可用，仅构建核心库和客户端
- `bm_init()` 在无渲染器时返回 false，需要补丁使 --version/--help 可用
---

**编译结束**: 2026-07-07 11:12
**最终状态**: built
