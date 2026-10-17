# soplex

SoPlex - Sequential object-oriented Simplex，ZIB 出品的线性规划（LP）求解器。

- **License**: ZIB Academic License（学术用途；LICENSE SPDX: LicenseRef-ZIB-Academic-License）
- **Language**: C++ (C++11)
- **Homepage**: https://soplex.zib.de/
- **Build system**: CMake

## 交付

- 静态库 `libsoplex.a` / `libsoplex-pic.a`
- CLI 求解器 `bin/soplex`（见 `commands.json`）
- 头文件（`soplex.h` 等）安装到 `include/`

## 版本

| 版本 | 说明 |
|------|------|
| 3.1.1 | 首次适配（HarmonyOS PC aarch64） |

## 已知要点

- 上游声明 `cmake_minimum_required(3.0.0)`，CMake>=4 需注入
  `CMAKE_POLICY_VERSION_MINIMUM=3.5`（配方 generate() 已处理）
- 依赖：gmp/6.3.0（exact 有理数求解）、zlib/1.3.1（gz 流 I/O）
- 上游测试：37+3 实例 × 8 settings = 320 个 ctest 用例，OHOS 全量通过