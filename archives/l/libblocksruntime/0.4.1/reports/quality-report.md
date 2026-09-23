# 质量报告 — libblocksruntime 0.4.1

## 配方完整性 (G1)

| 文件 | 状态 |
|------|------|
| `conanfile.py` | ✅ source/build/package/package_info/export_sources/apply_conandata_patches |
| `conandata.yml` | ✅ 官方发行归档 URL（deb.debian.org 主 + archive.ubuntu.com 备）+ sha256 |
| `test_package/conanfile.py` | ✅ 含 `test()` 且真实 `self.run()`（ctest） |
| `test_package/test_upstream.c` | ✅ 上游 `test/main.c` verbatim |
| `test_package/test_blocks_c.c` / `test_blocks_cpp.cpp` | ✅ 独立消费者（21 + 10 断言） |
| `test_package/MANIFEST.yml` | ✅ 上游测试声明（1）+ `assertion_count = 32` |

## 产物 (G4)

- `lib/libBlocksRuntime.a`
- `include/Block.h`、`include/Block_private.h`
- `licenses/LICENSE.TXT`（复刻自源码头部的 MIT/UIUC 双许可文本）

纯库类型（无 `bin/`），不需要 `commands.json`。

## 系统同名库隔离 (G3)

- 仅产出静态库 `libBlocksRuntime.a`；`libBlocksRuntime` 非系统同名库
  （OHOS 系统未提供此库，正是本适配要解决的问题）。

## 测试真实性 (R34)

- 三个消费者经 `find_package(BlocksRuntime)` + `BlocksRuntime::BlocksRuntime`
  链接安装后的静态库并 **真实运行**（ctest）。
- C++ 消费者不自行传 `-fblocks`，证明运行库确实传播了语言开关。
- 断言包含运行库内部状态观察（`isa` 类别、`BLOCK_NEEDS_FREE`、byref 共享、
  拷贝构造调用），非空壳链接。

## 版本策略 (R37)

- 任务版本 `0.4.1` = 发行版发布源码归档，`conandata.yml` 已声明下载 URL 的
  sha256；上游仓库 `mackyle/blocksruntime` 无 0.4.1 版本标识，已在此说明。

## 风险 / 已知限制

- 未使用上游 autotools（E007/E074，见 notes.md）；直接编译两个翻译单元。
- 运行库依赖 clang/GCC 内建原子操作。
