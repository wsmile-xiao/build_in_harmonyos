# Test Report — nsuds 0.7b (Ncurses Sudoku System)

- **Package**: nsuds/0.7b (上游 0.7B, AC_INIT([nsuds], [0.7B]))
- **Build system**: autotools (autoreconf bootstrap + configure + make)
- **Platform**: OHOS aarch64 (os=OHOS, arch=armv8, clang 15, Release)
- **Date**: 2026-09-03

## 上游测试情况

nsuds 上游**不含测试套件**：
- 源码树无 tests/ 目录；`src/Makefile.am` 无 `TESTS` 声明；
- `make check` 实际执行为 no-op（`Nothing to be done for 'check-am'`，exit 0）——
  在探索编译中真实运行验证过。

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无 |
| 集成测试 | 0 | 上游无 |
| 其他（make check） | 0 | no-op（exit 0），无实际用例 |
| **合计** | **0** | |

## 适配后测试（test_package）

nsuds 为纯交互式 ncurses 游戏，无脚本化游戏逻辑入口；但其 `--version/-v/--help/-h`
四个选项在任何 ncurses 初始化前 `exit(0)`（读 src/nsuds.c main() 确认），可用作
真实可验证的非交互 CLI。test_package/test.sh 对打包产物 `bin/nsuds` 真实执行并断言输出：

| 断言 | 命令 | 期望 | 实测 |
|------|------|------|------|
| 1 | `nsuds --version` | 输出含 `nsuds version 0.7B` | ✅ |
| 2 | `nsuds -v` | 输出含 `0.7B` | ✅ |
| 3 | `nsuds --help` | 输出含 `Usage: nsuds` | ✅ |
| 4 | `nsuds -h` | 输出含 `Usage: nsuds` | ✅ |
| 5 | `nsuds --help` | 输出含 `--no-color`（真实长选项） | ✅ |

- W3 本地 CI 模拟（setup.sh + build_and_test.sh）`exit_code=0`；
  test_package `test()` 输出 `[ok] nsuds version/help non-interactive CLI verified`。
- 打包产物同时含 bin/nsuds、share/doc/nsuds-0.7B/main（游戏内帮助）、
  share/man/man1/nsuds.1、var/games/nsuds/high_scores。

## 验证结果汇总

- 编译状态：**通过**（W3 conan create exit 0；conan-verify G0-G4/L2/L4/L5 全 PASS）
- 上游测试通过率：0/0（上游无测试）
- 适配后测试通过率：5/5（100%）
- conan-verify verdict：PASS；manifest 状态：built

## 修改上游测试用例

无（上游无测试用例，未修改任何上游测试）。

## 补全测试

上游无任何测试；适配后 test_package 补全了对打包二进制非交互 CLI 的真实执行
测试（5 条断言，见上）。
