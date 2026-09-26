# cheapglk 1.0.7 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-09-07
- 编译器: clang 15.0.4 (OHOS SDK)
- 状态: published
- CI: #49146 (OpenHarmonyPCDeveloper-CI-021) 通过

## CI 验证
| 目标 | 构建 | Worker |
|------|------|--------|
| PR #8763 | #49146 | OpenHarmonyPCDeveloper-CI-021 |

### 验证详情
- Conan test_package: 通过
- L0 门禁 (结构完整性): 通过
- L1 门禁 (测试执行验证): 通过

## AI 检视修复记录
- 2026-09-17: 提交 c028f7962d 修复 R34 测试门禁：test.c 失败路径改为 exit(1)
- 2026-09-17: 提交 c028f7962d 断言实际规范版本 0x00000706（Glk spec 0.7.6）
- CI #49146 通过，L1 测试执行验证通过

## PR 完整性检查 (2026-09-17)
- ✅ 分支上 archives/c/cheapglk/ 含 conandata.yml、conanfile.py、manifest.yaml、notes.md、README.md
- ✅ test_package/{CMakeLists.txt, conanfile.py, MANIFEST.yml, test.c} 完整
- ✅ 无 .log / 二进制等 R19 禁止文件
- ✅ reports/ 与 build/ 仅本地存在，未入库

## 编译步骤

```bash
# 交叉编译（Windows 宿主 → aarch64-linux-ohos）
conan create "archives/c/cheapglk/1.0.7" -pr:h=ohos-aarch64-windows-ll -pr:b=default --build=missing
```

CheapGlk 是纯 Unix Makefile 工程（无 configure、无 CMake、无依赖），生成
`libcheapglk.a`。配方通过 make 命令行参数注入工具链：

```bash
make CC="<clang>" AR="<llvm-ar>" RANLIB="<llvm-ranlib>" \
     CFLAGS="--target=aarch64-linux-ohos --sysroot=<sysroot> -O2" -j1
```

- make 命令行赋值优先级高于 Makefile 内的 `=` 定义（`CC = cc`、`OPTIONS = -g -Wall`
  会被命令行覆盖），无需 patch 即可注入交叉工具链。
- 库为纯静态库，无链接目标，`ar`/`ranlib` 负责归档。
- 打包：`libcheapglk.a` → `lib/`，`glk.h`/`glkstart.h`/`cheapglk.h` → `include/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make 报 `No rule to make target 'Studio/sdk/...'` | CC 指向 DevEco SDK 的 clang.exe 绝对路径含空格（`DevEco Studio`），cmd 下被分词 | 本机用 junction 指向 llvm 树（`C:\TEMP\opencode\ohos-llvm\bin\clang.exe`，无空格路径） |
| 2 | make 报 `unknown output-sync type '2'` | `CFLAGS=' -O2'` 单引号在 cmd.exe 下不解析，`-O2` 被 make 误当 `--output-sync` 选项 | CFLAGS 值去掉 shell 引号依赖，目标/优化 flags 由配方拼装无空格单值 |
| 3 | 编译产物是 COFF-x86-64（host 架构），链接器读作 `neither ET_REL nor LLVM bitcode` | 直接调 clang.exe 时未带 target 标志，编成宿主 ABI | 从 profile conf 读 `tools.build:cflags`/`sysroot`，经 CFLAGS 注入 `--target=aarch64-linux-ohos --sysroot=...` |
| 4 | CMake TryCompile 链接缺 `crtbeginS.o` / `libclang_rt.builtins.a`，路径解析到 `C:\TEMP\opencode\lib\clang\...` | junction 只指向 `llvm\bin`，破坏 clang 的 `../lib/clang` 相对查找 | junction 改为指向整个 `llvm` 树，clang 的 resource-dir 相对路径自动解析到真实 SDK 位置 |
| 5 | 链接重复 `main`：`duplicate symbol: main` | CheapGlk 自带 `main()`（main.o），且 test 程序又定义了 `main` | test_package 遵循 CheapGlk 框架：提供 `glk_main`/`glkunix_arguments`/`glkunix_startup_code` 三个用户回调，main 由库提供 |
| 6 | test_package 链接成功但本机无法运行 | test() 需 qemu-aarch64（本机未装），aarch64 OHOS 二进制无法在 Windows 宿主执行 | 沿用 game-music-emu 模式：cross_building 时若缺 qemu 则 `raise ConanInvalidConfiguration("qemu-aarch64 is required to run the OHOS test package")`；CI（Linux+qemu）负责运行验证 |

> 注：conan-verify 工具在本机 G2 阶段失败（`[WinError 2]`），是工具强制 build/host 同 profile
> 导致 build 侧用 OHOS clang 无法在 Windows 启动的环境限制，非配方问题；CI 为准。

## 源码修改

无补丁（纯 ANSI C 零依赖工程，工具链注入全部经 make 命令行完成）。

## 依赖版本

- clang/clang++ 15.0.4（OHOS SDK llvm，aarch64-linux-ohos target + sysroot）
- make: 本机用 mingw32-make 4.4.1（GNU Make 4.4.1 精简版）；CI 为 GNU make
- cmake 4.4.3（仅 test_package）
- llvm-ar / llvm-ranlib

## 验证结果

```bash
conan create "archives/c/cheapglk/1.0.7" -pr:h=ohos-aarch64-windows-ll -pr:b=default --build=missing
# 库交叉编译成功（libcheapglk.a，aarch64 ELF）
# test_package 交叉编译+链接成功（test_cheapglk）
# test() 本机停在 qemu 检查（合法信号，CI 运行）
```

## 注意事项

- CheapGlk 的 `main()` 由库提供：消费者程序不得再定义 `main`，应提供
  `glk_main`、`glkunix_arguments`、`glkunix_startup_code`。
- 库目标仅限静态（无 shared Makefile target）；package_type 设为 static-library。
- 源码 URL 用 github tag tarball（`cheapglk-cheapglk-1.0.7` 顶层目录），
  sha256 `9028335ec8f171552d8ff3dbe2f92d968c90b29ae9c6c6b1708e56c941f868bc`。

---

**编译结束**: 2026-09-07 14:40
**最终状态**: published