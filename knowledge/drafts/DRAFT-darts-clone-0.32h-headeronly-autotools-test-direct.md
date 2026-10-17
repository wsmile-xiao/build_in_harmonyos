# DRAFT-darts-clone-0.32h-headeronly-autotools-test-direct

> Contributor: 2301_76770579 | Status: Draft | Updated: 2026-09-09
> Source: darts-clone 0.32h HarmonyOS PC 适配（header-only + autotools 测试直跑）

## 现象

darts-clone 0.32h（s-yata，双数组 trie）是 **header-only** 库（单头
`include/darts.h`），但仓库自带 autotools（configure.ac/Makefile.am）。
若按惯性走 autotools：configure 生成物对库本体毫无必要，且老 autotools 在
OHOS/HMFS 上有一系列已知坑（config.guess 探针写盘被拒等）。

## 根因

- header-only 库的 autotools 只承担打包 + `make check` 驱动两个角色；
  **测试源码本身（test-darts.cc / test-tools.sh + mkdarts.cc/darts.cc）不依赖
  任何 configure 生成物**——`mkdarts-config.h`/`darts-config.h`/`lexicon.h`
  都是随包静态文件，`test-darts.cc` 只 include `<darts.h>` + 标准库。

## 解决方案

1. 配方按 header-only 处理：`package()` 只装 `include/darts.h`，
   `package_id` clear、`bindirs/libdirs` 置空。
2. **跳过 autotools，build() 内直接编译实跑上游测试**：
   - `test-darts.cc`：46 条 assert 自检（需 `-std=c++11`，`<random>`）；
   - `test-tools.sh`：编译 `mkdarts`/`darts` 两个 CLI（`-I include -I src`），
     按脚本相对路径语义（`../src/mkdarts`）摆 `src/test` 副本后原样运行，
     `cmp correct-dic`/`cmp correct-result` 字节级比对。
3. 断言依赖 `assert`：编译**不得加 `-DNDEBUG`**（-O2 不加即可）。

## 禁止策略

- 不得为 header-only 库硬跑 autotools（configure 生成物与库本体无关，徒增 HMFS
  探针风险）。
- 不得改 `test-tools.sh` 的相对路径——摆目录副本比改脚本更可复现。
- 不得加 `-DNDEBUG`（会把 46 条 assert 全部空化，测试变空壳）。

## 适用范围

所有 header-only C++ 库（单头/少头）+ 上游 autotools 仅作测试驱动的场景：
跳过 configure，直接编译测试源实跑。
