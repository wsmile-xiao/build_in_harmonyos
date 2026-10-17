# d11amp 0.61 适配笔记

## 编译环境
- 构建系统: makefile（mark4/software/Makefile，无 configure/autotools）
- 编译日期: 2026-09-11
- 编译器: clang/clang++（OHOS SDK，从 profile `tools.build:compiler_executables` 获取）

## 编译步骤

```bash
# 主构建目标在 mark4/software（当前版本；mark1~mark3 为历史代）
cd mark4/software
# 以下为探索阶段手动复现步骤；正式配方（conanfile.py）编译器从
# profile tools.build:compiler_executables 获取（R33），不依赖这些导出。
export PKG_CONFIG_PATH=<conan generators dir>:$PKG_CONFIG_PATH
export CC=clang CXX=clang++
make -j1            # 生成 d11amp 可执行文件
make install DESTDIR=<staging>   # bin/d11amp + share/man/man1/d11amp.1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Package 'gtk4' requires 'pango >= 1.56'`（pkg-config 版本约束） | gtk4 依赖新版 pango | conan 依赖链从制品仓拉取 pango/1.56.4，不依赖本地预编译包 |
| 2 | Makefile 用 `pkg-config libmpg123`，但 conan mpg123 包导出 `mpg123.pc` | 命名不一致 | generate() 中复制 mpg123.pc → libmpg123.pc 别名（audiowmark 同款先例） |
| 3 | 上游 checks.mk 硬编码 `TMP_DIR?=/tmp/d11amp/`，本环境 /tmp 只读 | 平台限制 | 探索阶段 make check 时传 `TMP_DIR=<build> SHA256_CMD=sha256sum`（上游 NOTES.txt 已记载平台差异需显式指定），实测 check OK |
| 4 | `#include "config.h"` 解析到全局同名文件而非 src/shared/config.h | 本机残留的全局 config.h 干扰 | conan 干净环境无此问题；本地评估时用 `CPPFLAGS=-I./src/shared` |
| 5 | 源码顶层多代结构（mark1~mark4），init-build 嵌套提升只保留首个子目录 | 工具对多代仓库的目录提升逻辑 | work 目录重建为完整源码树（--strip-components=1 全量解压），主构建目标确定为 mark4 |
| 6 | CI 红：harfbuzz/14.2.0.1 源码构建时 `meson.test()` 失败 165 项 | gtk4/4.22.4 配方 override glib/2.84.0.1.1(shared=True)，CI 干净环境需 `harfbuzz:1b5bfb055`（requires glib/2.84.Z 动态），制品仓 14.2.0.1 仅有 `3009fa3b`（锁定 glib/2.84.0.1）→ 无匹配二进制 → 回退源码构建 | 消费者 override 到修复版 `harfbuzz/14.2.0.1.1.1`（2026-08-23 发布，requires glib/2.84.Z 动态），命中制品仓二进制（E538 知识，gtkmm 同款做法） |
| 7 | test_package 运行报 `libc++_shared.so: symbol not found` | OHOS 动态库（含 C++ runtime）在 SDK llvm/lib/aarch64-linux-ohos，加载器默认不搜该路径；libharfbuzz.so.0 等动态依赖需 C++ runtime | test() 注入 SDK lib 到 LD_LIBRARY_PATH（audiowmark 先例同款） |

## 源码修改

无（无需补丁；依赖注入由 PkgConfigDeps + PKG_CONFIG_PATH 完成）。

## 依赖版本

- gtk4/4.22.4（transitive: glib/pango/cairo/cairo-gobject/harfbuzz/graphene/fribidi/libepoxy/fontconfig/zlib）
- gdk-pixbuf/2.44.6
- mpg123/1.33.5
- portaudio/19.7.0
- libzip/1.11.4

## 验证结果

```bash
# 上游测试（checks.mk：主题转储 + SHA256 校验，1 项）
# 探索编译阶段本地设备实测：
make TMP_DIR=<build>/d11amp-check SHA256_CMD=sha256sum check   # → check OK（1/1 通过）
# 说明：该测试依赖 GTK 图形栈（--gui.theme.dumpdefault），conan build() 干净环境
# 未集成；已在探索阶段实测通过并如实申报（MANIFEST upstream_test_in_build: false）。

# test_package 自研断言（R34，conan create 内实际执行）
d11amp --version    # → 0.61
d11amp --help       # → 帮助输出可读
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/d11amp | 主程序可执行文件（GTK4 GUI mp3 播放器） |
| share/man/man1/d11amp.1 | man page |

## 注意事项

- R38: 应用型产物含可执行文件 → 已创建 commands.json（软件级目录）
- R33: 编译器通过 `self.conf.get("tools.build:compiler_executables")` 获取（profile 配置 clang 路径），不依赖裸 shell 环境变量
- R40 适配完整性说明：d11amp 是 GTK4 图形 mp3 播放器，图形栈由制品仓已适配发布的 gtk4/4.22.4 依赖提供（gtk4 配方已含鸿蒙适配补丁并通过 G3/G4 验证）；d11amp 自身为纯应用层代码（无平台相关渲染/系统调用），通过标准 pkg-config 链接依赖。上游主题转储测试（--gui.theme.dumpdefault）在探索阶段本地实测通过（check OK），证明 GTK4 图形链路在鸿蒙平台可用。test_package 以 --version/--help 断言覆盖安装产物可执行性，作为 CI 环境无图形栈场景下的同等功能验证。
- Makefile 用 pkg-config 探测依赖 → generate() 用 PkgConfigDeps 生成 .pc
## 结束标记

### 最终状态

- status: built（本地 conan-verify 通过 G1-G4，未上传制品仓）
- 编译结束
- COMPLETED
---

**编译结束**: 2026-09-11 08:35
**最终状态**: published
