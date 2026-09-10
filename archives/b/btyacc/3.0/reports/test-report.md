# btyacc 3.0 测试报告

## 测试环境
- 平台: HarmonyOS PC (aarch64, OHOS 6.0)
- 编译器: clang 15.0.4 (toolchain: /data/service/hnp/bin/clang)
- 构建方式: `make CC=clang LINKER=clang -j1`（纯 Makefile 工程，无 configure）
- 日期: 2026-09-05

## 上游测试

btyacc 上游自带 `test/*.y` 语法文件，无 `make check` 目标；用 btyacc 本体解析验证。

| 测试文件 | 结果 |
|----------|------|
| test/ansiC.y | ✅ PASS（生成解析器） |
| test/ansiC2.y | ✅ PASS |
| test/error.y | ✅ PASS |
| test/ftp.y | ✅ PASS |
| test/t1.y | ✅ PASS |
| test/t2.y | ✅ PASS |
| test/test.y | ✅ PASS |

上游测试 7/7 通过，均生成 y_tab.c / y_tab.h（`btyacc -d <grammar>`）。

## test_package 消费者冒烟测试（R34）

`test_package/test.sh`：btyacc 解析最小 grammar 并验证生成 out_tab.c / out_tab.h。
- 命令: `btyacc -d -b <prefix> <mini.y>`（btyacc 要求选项在文件名前）
- 结果: ✅ PASS（conan create 的 test_package 阶段实际执行通过）

## Conan 验证门禁（conan-verify）

| 门禁 | 结果 |
|------|------|
| G1 配方完整性 | ✅ PASS |
| G2 conan create（干净构建） | ✅ PASS |
| G3 系统同名库隔离（R26） | ✅ PASS |
| G4 产物完整性 | ✅ PASS |
| L2 平台功能矩阵（smoke） | ✅ PASS |
| L4 静态安全扫描 | ✅ PASS |
| L5 产物基线 | ✅ PASS |

## W3 本地 CI（finish 内嵌）

`build_and_test.sh btyacc/3.0`：✅ PASS（1/1，100%），JC5 基线隔离复验后通过（见基线隔离审计）。

## 测试断言统计

- 上游语法测试: 7 项（btyacc 解析成功判定）
- test_package 冒烟: 2 项（out_tab.c 与 out_tab.h 存在且非空）
- 合计断言数: 9