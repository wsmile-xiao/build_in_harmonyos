# rgbds 1.0.1 适配笔记

## 编译环境

- 构建系统: makefile（上游 GNU Makefile，无 configure）
- 语言: C++20（Makefile 硬编码 `-std=c++20`，clang 15 支持）
- 编译日期: 2026-09-20
- 编译器: clang/clang++（GnuToolchain + conf 注入）
- 状态: **真机 shadow CI 验证通过**（L0/L1/L4/L5 pass，见下）

## 上游信息

- 仓库: https://github.com/gbdev/rgbds
- tag: v1.0.1（commit 92bfe5d930c07dd4672b148f811305aa294d6e6f）
- 许可证: MIT
- 产物: rgbasm（汇编器）、rgblink（链接器）、rgbfix（ROM 头修复）、rgbgfx（PNG↔tile 转换）

## 构建步骤

1. `bison` 生成 parser 源码（`src/asm/parser.*`、`src/link/script.*`）——tag 归档不含生成的 parser。
2. `make -j1 CXX=clang++ CXXFLAGS="-O2 -DNDEBUG" STRIP=true PKG_CONFIG=true PNGCFLAGS=... PNGLDFLAGS=... PNGLDLIBS=...`
3. 手动 `copy()` 打包 4 个二进制 + LICENSE + man（上游 `make install` 依赖 GNU `install`，toybox 无此命令）。

## 关键决策与适配要点

| 项 | 决策 | 原因 |
|---|---|---|
| 构建系统 | Makefile（非 CMake） | 上游主构建路径；CMake 的 `cmake_minimum_required(3.9..3.17)` range + CMake 4.x 有 E103 兼容风险 |
| bison | `tool_requires("bison/3.8.2")` + 配方内直接调用 | tag 归档无 parser；绕开 `src/bison.sh`（依赖 `/bin/sh` + `sed -E`，toybox 不可靠） |
| BISON_PKGDATADIR | 指向 `bison 包/share/bison` | **真机实测**：bison/3.8.2 编译时 datadir 被配成绝对 `/share`，运行时找不到 `m4sugar.m4`；需显式重定向到包内 m4 宏 |
| libpng | `requires("libpng/1.6.58.2")` + 手动传 PNG 三组 flag | 绕开 pkg-config 工具依赖（Makefile 反引号探测改为 `PKG_CONFIG=true` no-op） |
| CXXFLAGS | 覆盖为 `-O2 -DNDEBUG` | 去掉上游默认 `-flto`（交叉 LTO 插件不可用） |
| STRIP | `STRIP=true` | OHOS MAC 拒绝 strip 后的 ELF（E077 相关），产物签名由 CI sign.sh 处理 |
| 打包 | `copy()` 手动打包 | E098：toybox 无 `install` 命令，不依赖 `make install` |
| 版本字符串 | 依赖 `version.cpp` fallback | tag 归档无 `.git`，`VERSION_STRING` 为空 → fallback 到 `v1.0.1` |

## 依赖版本（已在制品仓 ohpcd 确认）

- libpng/1.6.58.2（运行期，仅 rgbgfx；传递依赖 zlib/1.3.2）
- bison/3.8.2（构建期，生成 parser）

`conan list -r=ohpcd` 确认二者 recipe 均在制品仓（libpng 1.6.39/1.6.58/1.6.58.1/1.6.58.2/1.6.58.3；bison 2.7/3.8.2）。

## 真机 shadow CI 结果（2026-09-21）

```text
L0_RESULT=pass  (R36/R37/R38 quality gates)
L1_RESULT=pass  (test_package executed；L1e 破坏性负向测试确认测试真依赖包产物)
L2_RESULT=pass  (rgbasm/rgbfix/rgblink --version OK；rgbgfx 因动态链接 libpng 无 runenv 时 --version 失败，non-blocking)
L4_RESULT=pass  (patches clean — 5 个 OHOS 适配补丁)
L5_RESULT=pass  (bin/ has content)
upstream internal tests: 1606/1606 passed (asm 827 + link 105 + fix 441 + gfx 233)
test_package: "rgbds functional assertions passed"（8 条断言）
Build Summary: Total 1, Success 1, Failed 0
```

- L2 的 rgbgfx `--version` 失败是**预期行为**：rgbgfx 动态链接 libpng16.so，CI 的 L2 smoke test 直接运行 bin 二进制（无 `conanrun` 的 `LD_LIBRARY_PATH`）。test_package 内 `env="conanrun"` 已正确注入，rgbgfx 正常工作；L2 属 non-blocking warning。
- shadow runner 默认跳过 `ci/conan/setup.sh`（负责添加 `ohpcd` remote 并禁用 `conancenter`）。首次运行因 conan 走 `conancenter` 报 "libpng/1.6.58.2 not resolved"，手动在 job 的 `CONAN_HOME` 里 `conan remote add ohpcd ...` + `conan remote disable conancenter` 后恢复。正式 CI 由 setup.sh 自动完成，无需配方处理。

## 上游 internal 测试在 OHOS 上的适配补丁（5 个）

| 补丁 | 问题 | 修复 |
|---|---|---|
| 0001 run-tests shebang | `./test.sh` 的 `#!/usr/bin/env bash` 在 OHOS 无 `/usr/bin/env`（E037） | 改用 `"$BASH" ./test.sh` |
| 0002 gfx PNG flags | gfx 测试辅助工具 make 用反引号 `pkg-config`（OHOS 无） | make 调用从环境变量转发 `PNGCFLAGS/PNGLDFLAGS/PNGLDLIBS` |
| 0003 fix $PWD | `src="$PWD"` 在 OHOS bash getcwd 失败时 unbound | 改用 `$(cd "$(dirname "$0")" && pwd)` |
| 0004 gfx 进程替换 | stdin 变体 `diff <(sed ...)` 的 `/dev/fd` 在 OHOS 受限 | 改用临时文件 |
| 0005 gfx posix_spawn | `posix_spawn(..., nullptr)` 不传 environ，子进程丢 `LD_LIBRARY_PATH` | 传 `environ` |

## test_package 修复记录（真机驱动）

| 问题 | 根因 | 修复 |
|---|---|---|
| `PWD: unbound variable` | OHOS 上 bash 启动时 getcwd 失败，`set -u` 下 `${TMPDIR:-$PWD}` 触发 | workdir 改用 `${TMPDIR:-${HOME:-/data/service/hnp}}` |
| ROM size 断言失败 | rgblink 对最小程序 pad 到 16 KiB（0x4000），非 32 KiB | 断言 `>=16384` |

## 注意事项

- upstream **internal** 回归套件（`test/run-tests.sh --only-internal`，1606 个测试）已在配方 `build()` 内集成并全通过；
  **external** 下游项目测试需 `fetch-test-deps.sh` 拉取外部代码库，配方内不运行。
- 产物为命令行工具，已声明 `commands.json`（R38）。
- 4 个二进制均动态链接 libpng16（仅 rgbgfx 实际使用），消费者需经 `conan runenv` 获得 `LD_LIBRARY_PATH`。
