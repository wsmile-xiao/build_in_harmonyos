# trimal 1.5.1 适配笔记

## 基本信息
- 上游: trimAl v1.5.1（https://github.com/inab/trimal，tag v1.5.1，commit d637091）
- 构建系统: 手写 Makefile（source/makefile，无 configure / CMake / meson）
- 编译器: OHOS SDK clang/clang++ 15.0.4（aarch64-linux-ohos）
- 产出: bin/trimal、bin/readal、bin/statal
- 状态: built

## 编译步骤
1. `get()` 下载官方 tar 包 https://github.com/inab/trimal/archive/refs/tags/v1.5.1.tar.gz
   （sha256 `58751054861b152e92214ff8c01a132071230614e8e777a7c9280d03648cde3b`，strip_root）
2. `make CC=<conan conf: tools.build:compiler_executables.cpp> -j1`（cwd = 源码根/source）
3. 上游 dataset 回归套件（504 用例）在 build() 内执行：
   `bash scripts/generate_trimmed_msas.sh && bash scripts/compare_trimmed_msas.sh`
4. 打包 bin/trimal、bin/readal、bin/statal 与 licenses/LICENSE

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 硬编码 `CC = g++` | 上游只面向桌面 GCC | make 命令行覆盖 `CC=<conan cpp compiler>`，零补丁 |
| 2 | 上游测试脚本无 shebang 且调用 ELF | GitHub Actions 用 bash 执行 | conanfile 中显式 `bash scripts/...`（OHOS /system/bin/sh 不能执行 ELF） |
| 3 | 测试脚本用相对路径 `./source/trimal`、`dataset/...` | 脚本假定在仓库根运行 | cwd 设为源码根（strip_root 后是完整仓库树），原样运行 |

## 源码修改
无补丁。上游源码零修改，仅通过 make 变量覆盖编译器。

## 依赖版本
无第三方依赖（仅 OHOS SDK 的 libc++/libm）。

## 上游测试清点与实测（R51）
- `tests/` 目录: 无；ctest: 无（非 CMake）；pytest: 无；Makefile 无 `check` 目标。
- 上游回归实现于 `.github/workflows/build.yml` 的 test job：
  `source/trimal && ./scripts/generate_trimmed_msas.sh && ./scripts/compare_trimmed_msas.sh`
- 用例清点: 84 个 dataset 输入 × 6 种模式（gappyout/strict/strictplus/automated1/nogaps/noallgaps）= 504。
- 实机实测（2026-09-26，HarmonyOS PC aarch64，clang 15.0.4，本地构建二进制）:
  504/504 与 `dataset/trimmed_msas/` 参考输出逐一 diff 一致（generate 1143s + compare 42s，exit 0）。
  日志: `reports/upstream-tests.log`（精简证据；完整输出可用 `run_upstream_tests.sh` 重现）。
- conanfile.py 的 build() 已集成同一套件，`conan create`（W3/CI）时自动复跑。

## 验证结果
```bash
make -C source CC=$CXX -j1        # 3 个二进制构建成功（仅 1 条上游 using-namespace 告警）
trimal --version                  # trimAl v1.5.rev1 build[2025-11-25]
bash scripts/generate_trimmed_msas.sh   # 生成 504 个 MSA（含上游既有 WARNING 输出）
bash scripts/compare_trimmed_msas.sh    # 504/504 diff 一致，exit 0
```

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| bin/trimal | ~290 KB | 主修剪工具 |
| bin/readal | ~238 KB | 比对读取/信息/格式转换 |
| bin/statal | ~246 KB | 比对统计 |
| packaging/trimal-1.5.1-ohos-aarch64.tar.gz | 见文件 | release 包（conan package 目录打包） |

## 注意事项
- 上游 `-gt V` 的实际语义为“删除缺口比例 > (1-V) 的列”（main.cpp: `gapThreshold = 1 - atof(argv[i])`），与帮助文本字面相反；该行为已被 dataset 参考输出固化，适配未改动。

**编译结束**: 2026-09-26
---

**编译结束**: 2026-09-26 15:45
**最终状态**: built
