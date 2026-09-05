# afl++-tools

AFL++ (a fast instrumented coverage-guided fuzzer) 的鸿蒙 PC (arm64) 适配。

- 上游：https://github.com/AFLplusplus/AFLplusplus
- 许可证：Apache-2.0
- Conan 包名：`afl++-tools`（conan slug 允许 `+`，如 vera++；与目录名、分支名一致）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 4.40c | built | 鸿蒙 PC 实机验证完成（2026-09-04，19/19 explicit） |

## 版本差异要点（4.40c vs 4.33c）

- PROGS 新增 `afl-cmin`（make 目标 = `cp -f afl-cmin.py afl-cmin`，仍是 Python 实现；`src/afl-cmin.c` C 重写尚未被上游启用）
- SH_PROGS：`afl-cmin` → `afl-cmin.awk`
- 补丁：0001/0002 重打（头部新增 unistd.h 等）；0003/0004 上游已修删除；0005 重打
- 详见 `4.40c/notes.md` 与 `md汇总/留痕工作/afl-tools/aflplusplus-4.40c差异分析.md`
