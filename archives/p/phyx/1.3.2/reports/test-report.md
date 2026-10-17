# phyx 1.3.2 测试报告

> **项目**：phyx 1.3.2（系统发育序列、树与连续性状 CLI 工具集）
> **测试日期**：2026-10-12
> **测试环境**：HarmonyOS PC aarch64，clang 15.0.4，Conan 2.29.1 OHOS 适配版
> **测试类型**：上游回归、消费者确定性数据测试、ELF 数学后端闭包审计

## 一、测试摘要

| 测试层级 | 用例数 | 结果 |
|----------|-------:|------|
| 上游 Linux 基线 | 100 | 100/100 精确通过 |
| HarmonyOS 上游回归 | 100 | 100/100 被上游 runner 接受：95 项精确匹配，5 项为上游声明的随机预期差异 |
| 新增消费者测试 | 3 | 3/3 通过 |
| HarmonyOS 特有测试 | 1 | 1/1 通过 |
| **适配后总计** | **104** | **104/104 通过** |

构建并打包 47 个 CLI。上游 runner 另报告 `pxtcol`、`pxtcomb` 两个程序没有上游
测试，本次消费者测试已补齐二者。

## 二、问题与修复验证

上游 `configure.ac` 用 `AC_SEARCH_LIBS` 探测 Armadillo，但手写 `Makefile.in` 的最终
链接线没有消费 `@LIBS@`，而是硬编码 reference BLAS/LAPACK 和 Armadillo。原始
OHOS 链接首先出现 `_FortranA*` 未定义；简单追加 FortranRuntime 虽可链接，却会让
可执行文件同时静态定义 BLAS/LAPACK 符号，并通过 Armadillo 动态装载 OpenBLAS。

修复后仅注入依赖搜索目录，让 Autoconf 选择并记录数学提供者；最终链接统一消费
`@LIBS@`。构建期对代表性 `pxseqgen` 同时执行动态依赖和普通符号表检查：

- `DT_NEEDED` 不含 `libblas`、`liblapack`、`libFortranRuntime`、`libFortranDecimal`；
- 可执行文件不定义 `dgemm_`、`dgesv_`、`dgetrf_`；
- 真机日志输出 `OHOS math-provider check: Armadillo only`。

此外使用同一份 `pxseqgen` 目标文件完成三臂对照：

| 实验臂 | 链接线差异 | 退出码 | ELF/符号结论 |
|--------|------------|-------:|---------------|
| A 原始 | reference `-llapack -lblas`，无 Flang runtime | 2 | `_FortranA*` 未定义，链接失败 |
| B 假修复 | 在 A 末尾追加 `FortranRuntime/FortranDecimal` | 0 | 静态定义 `dgemm_`、`dgesv_`、`dgetrf_`，且 Armadillo→OpenBLAS 动态闭包仍在 |
| C 正确 | 只保留 Autoconf 选择的 Armadillo 提供者 | 0 | 禁止依赖和嵌入符号均为零，程序实际执行成功 |

脱敏的命令、输出摘录和原始日志 SHA256 见 `path-b-evidence.md`。该实验把“失败复现—
错误修复反例—正确修复”闭合为可复核证据，不以文字推断代替实际链接。

## 三、测试详情

### 3.1 上游测试

上游 `src/run_tests.py` 共注册 100 项集成测试。未经适配的 Linux 基线实测为
`PASSED PROGRAMS: 45 (100 tests)`、`FAILED PROGRAMS: 0 (0 tests)`。HarmonyOS 真机
执行相同 runner，95 项输出精确匹配；`pxbdsim`、`pxboot`、`pxpoly` 的 5 项随机数据
比较由上游 runner 列入 `anticipated failures (random numbers)`，runner 成功退出，
没有真实失败。未修改、删减或绕过任何上游测试。

### 3.2 新增消费者与 HarmonyOS 测试

| 测试 | 验证内容 | 结果 |
|------|----------|------|
| `pxlssq` 固定输入 | 核苷酸统计结果逐字段确定性比对 | PASS |
| `pxtcol` | 上游未覆盖程序的确定性 NEXUS 输出 | PASS |
| `pxtcomb` | 上游未覆盖程序的参考树组合结果 | PASS |
| `pxseqgen` HarmonyOS 闭包 | 真实执行依赖 Armadillo/OpenBLAS 的科学计算路径 | PASS |

测试入口为 `test_package/test_phyx.py`，由 `test_package/conanfile.py::test()` 在
`conan create` 中实际执行。

## 四、门禁结果

- 真机 `conan create`：PASS，退出码 0；47 个 CLI 均完成编译、打包。
- 真机完整 `build_and_test.sh` W3：PASS，退出码 0；CI 复现的
  `config.status conf*/subs1.awk: Permission denied` 已消失。
- Conan G0/G1/G2/G3/G4：PASS。
- 单一数学提供者 ELF 门禁：PASS。
- 消费者测试：4/4 PASS。
- 源码 URL 与 SHA256：官方 tag `v1.3.2`，SHA256 校验通过。

## 五、复现命令

```bash
conan create archives/p/phyx/1.3.2 \
  -pr:h ci/conan/profiles/ohos-aarch64 \
  -pr:b ci/conan/profiles/ohos-aarch64 \
  --build=phyx/1.3.2
```

完整真机日志保存在工作区外的
`.task-results/phyx-1.3.2/logs/native-conan-ci-fix-r5.log`，避免把运行日志和构建产物
混入提交。原始日志 SHA256 为
`7c3cbdf269cb1490f297b4687a3a5ce0ef4492d07cd3886d4a260728e9a96540`，对应 Conan
recipe revision `8c3f7476b102ca2185ea9a09dfbde65d`。同一最终配方的完整 W3 日志
SHA256 为 `eccdf65e1d44cdd84b320d1238cb876928661eab3bb387a1901de10b9b5ecf05`；三臂证据日志
SHA256 为 `5a20094e3977b9726db529253af8f11453e6dfc859ce833f15da5bf9e5a5c5c5`。
