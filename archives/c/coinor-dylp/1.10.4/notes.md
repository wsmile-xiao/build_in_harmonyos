# coinor-dylp 1.10.4 适配笔记

## 编译环境
- 构建系统: autotools（COIN-OR 递归 configure：顶层 + DyLP/ 子目录）
- 编译日期: 2026-08-07
- 编译器: clang/clang++ (15, libc++)
- 状态: built

## 编译步骤

1. 下载源码: `https://github.com/coin-or/DyLP/archive/refs/tags/releases/1.10.4.tar.gz`
2. 最小补丁（patches/，由 conanfile.py 的 apply_conandata_patches 应用）：
   - `0001-config.guess.patch` / `0003-DyLP-config.guess.patch`：给 2007 版 config.guess
     增加 HarmonyOS (HongMeng) 与 aarch64 Linux 分支（顶层 + DyLP/ 子目录各一份）
   - `0002-config.sub.patch` / `0004-DyLP-config.sub.patch`：给 2007 版 config.sub
     增加 aarch64 CPU 与 linux-musl OS 识别（3 处，顶层 + DyLP/ 子目录各一份）
   - 共 94 行，避免了整体替换 2024 版文件带来的超大 diff
3. configure（关键命令）：
   ```bash
   ./configure --prefix=/ \
     --with-coinutils-incdir=<CU>/include/coin \
     --with-coinutils-lib="-L<CU>/lib -lCoinUtils -lz -lm" \
     --with-osi-incdir=<OSI>/include/coin \
     --with-osi-lib="-L<OSI>/lib -lOsi -L<CU>/lib -lCoinUtils -lz -lm" \
     --build=aarch64-unknown-linux-musl --disable-dependency-tracking \
     --disable-shared --enable-static
   ```
4. 修补 config.status（顶层 + DyLP/）后重跑：mktemp→mkdir -p ./conftmp、umask 077→022
5. `make -j1`
6. `make install`（conan 打包用 autotools.install()）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | dylp 自带 config.sub 为 2007 版，`aarch64-unknown-linux-musl` 不被识别 | 版本过旧 | 最小补丁：config.sub 加 aarch64/musl 支持，config.guess 加 HarmonyOS/aarch64 分支（共 94 行，避免整体替换 2024 版的大 diff） |
| 2 | config.status 报 `confstat*/in: Permission denied` | HMDFS umask/mktemp | sed 修补：mktemp→mkdir -p ./conftmp、umask 077→022，重跑 config.status |
| 3 | libOsiDylp 链接失败：`//lib/libCoinUtils.la` 无效 | conan relocatable 打包改写 .la dependency_libs 绝对路径 | build() 中恢复 .la 内真实绝对路径 |
| 4 | libOsi.a 非 PIC 导致共享库链接失败 | 上游 Osi 仅提供非 PIC 静态库 | dylp 改为 `--disable-shared --enable-static` 纯静态构建 |
| 5 | conan 2 export_sources 用 self.copy 报错 | Conan 2 移除 self.copy | 改用声明式 `exports_sources = "patches/*"` |
| 6 | test_package 编译 `dy_isscaled` 未声明 | 该函数在 `#ifdef DYLP_INTERNAL` 保护区，客户端不可见 | 改用公开 API `dy_defaults()` |
| 7 | conan-verify G2 报 `/bin/sh: syntax error: unexpected '('` | verify 脚本未对含空格/括号路径加引号 | scripts/ohc/conan_verify.py 用 shlex.quote 引用路径 |

## 源码修改

- 4 个最小补丁（patches/，共 94 行）：
  - `0001-config.guess.patch` / `0002-config.sub.patch`：顶层 config.guess/config.sub
  - `0003-DyLP-config.guess.patch` / `0004-DyLP-config.sub.patch`：DyLP/ 子目录
- 均为对 2007 版文件的最小改动（不整体替换 2024 版）：
  - config.guess：`case "${UNAME_MACHINE}:${UNAME_SYSTEM}:..." in` 中新增
    `*:HarmonyOS:*:*|*:HongMeng:*:*` 与 `aarch64:Linux:*:*` 分支，直接输出
    `${UNAME_MACHINE}-unknown-linux-musl`
  - config.sub：kernel-OS 拆分段加 `linux-musl*`、CPU 表加 `aarch64 | aarch64_be`、
    OS 表加 `-linux-musl*`

## 依赖版本

| 依赖 | 版本 |
|------|------|
| coinutils | 2.11.13 |
| coin-or (Osi) | 0.108.12 |
| zlib | 1.3.1 |

## 验证结果

- `make check`：dylp test/ 子目录在 OsiTests 缺失时跳过；手动编译运行 `unitTest` 全部通过
  （dytest_problems/rays/solutions/tableau 各断言 pass，EXIT=0）
- `conan-verify coinor-dylp 1.10.4`：G0-G5 + L2/L4/L5 全部 PASS
- `conan create` 内 test_package：编译链接 libOsiDylp/libDylp 并调用 dy_defaults()，测试通过
- finish W3 本地 CI（setup.sh + build_and_test.sh）：通过，.ci-result.json exit_code=0

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | conan 配方（EPL-1.0，依赖 coinutils/coin-or/zlib） |
| conandata.yml | 源码 URL 列表 + sha256 |
| patches/*.patch | 4 个 config.guess/config.sub 升级补丁 |
| test_package/ | L1 消费者测试（test.cpp 调用 dy_defaults） |
| manifest.yaml / notes.md | 归档元数据与笔记 |

## 注意事项

- 库名：libDylp（核心）+ libOsiDylp（Osi 接口），cpp_info.libs = ["OsiDylp", "Dylp"]
- 许可证：EPL-1.0（注意不是 EPL-2.0）
- dylp 头文件位于 include/coin/，且 dylp.h 内部用 `#include <dylib_io.h>`，
  cpp_info.includedirs 需含 include/coin 与 coinutils/coin-or 的 include/coin
