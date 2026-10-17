# 上游测试资产清单 — enzyme 0.0.284

> **报告目的**: 真实统计上游 enzyme/test 下 lit 测试资产数量与入口，替代 PR 正文中"上游无测试"的错误勾选。
> **生成日期**: 2026-07-23
> **数据源**: enzyme 0.0.284 源码树（`~/.conan2/p/enzym*/s/enzyme/test/`）
> **知识库**: E216-draft-enzyme-llvm-sdk-lit-ohos（路径 B 候选支撑）

## 入口文件（均存在）

| 入口 | 路径 | 存在 | 说明 |
|------|------|------|------|
| CMakeLists.txt | enzyme/test/CMakeLists.txt | ✅ | configure_lit_site_cfg 生成 lit.site.cfg.py |
| lit.cfg.py | enzyme/test/lit.cfg.py | ✅ | lit 测试配置（测试发现规则、超时、substitutions） |
| lit.site.cfg.py.in | enzyme/test/lit.site.cfg.py.in | ✅ | lit 站点配置模板（由 CMake 填充路径） |
| ninja check-enzyme | enzyme/test/CMakeLists.txt 中 add_lit_target | ✅ | 上游 lit 测试执行入口 |
| llvm-lit / lit | PATH 或 SDK | ❌ | **未安装**（lit exit=1, llvm-lit exit=1） |
| FileCheck | /data/service/hnp/bin/FileCheck | ✅ | 存在但非 SDK 自带，部分用例可能路径不匹配 |
| llvm-tblgen | SDK llvm/bin/llvm-tblgen | ❌ | **SDK 缺失**（exit=1），TableGen .inc 无法生成 |

## 数量统计

### 统计命令

```bash
SRC=/storage/Users/currentUser/.conan2/p/enzym37bdfa716b6f4/s/enzyme
# test/ 下所有文件总数
find "$SRC/test" -type f | wc -l
# 主要测试源文件 (.ll/.c/.cpp/.cu/.f90/.mlir/.rs)
find "$SRC/test" -type f \( -name "*.ll" -o -name "*.c" -o -name "*.cpp" -o -name "*.cu" -o -name "*.f90" -o -name "*.mlir" -o -name "*.rs" \) | wc -l
# .ll 文件数（lit 主要用例）
find "$SRC/test" -type f -name "*.ll" | wc -l
```

### 执行结果（退出码 0）

| 指标 | 数量 |
|------|------|
| test/ 下所有文件总数 | **1523** |
| 主要测试源文件（.ll/.c/.cpp/.cu/.f90/.mlir/.rs） | **1471** |
| .ll 文件数（lit 主要用例） | **1180** |

### 工具可执行性（退出码）

| 工具 | 路径 | exit code |
|------|------|-----------|
| lit | PATH | 1（未安装） |
| FileCheck | /data/service/hnp/bin/FileCheck | 0 |
| llvm-lit | PATH | 1（未安装） |
| llvm-tblgen | SDK llvm/bin/ | 1（SDK 缺失） |
| ninja | /data/service/hnp/bin/ninja | 0 |

## 上游测试执行结论

**首个真实失败**: `lit` 命令未安装（exit=1），`llvm-tblgen` SDK 缺失（exit=1）。

**替代验证方案**: 由于 OHOS SDK LLVM 15 缺少 lit/llvm-lit/llvm-tblgen，上游 1523 个 lit 测试用例无法在 OHOS CI 中执行。test_package 提供 nm -D 符号存在性检查 llvmGetPassPluginInfo 作为替代验证（不触发 relocation），但**不能覆盖上游 lit 未执行**。

## PR 正文正确写法

- ❌ 禁止勾选"上游无测试"（上游有 1523 个 lit 测试文件）
- ✅ 上游测试通过率写 **0/1523**（未执行/未全量执行，原因：OHOS SDK LLVM 15 缺少完整 lit/FileCheck/opt/TableGen/tblgen 与 LLVM CMake 导出组件）
- ✅ test_package 单独统计替代验证 N/N

---

*evidence: upstream-test-inventory.md · 2026-07-23 · PR !2786 · E216 draft*