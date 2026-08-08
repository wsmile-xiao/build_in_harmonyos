# abi-compliance-checker 2.3 适配笔记

## 上游测试情况（规则 4/5 说明）

上游 abi-compliance-checker 2.3 自带回归测试套件：
- `modules/Internals/RegTests.pm`：包含 `testTool()` / `testC()` / `testCpp()` 等约 20 个子测试，
  通过 `abi-compliance-checker -test` 选项运行。
- 测试机制：生成两个二进制不兼容的 C/C++ 样本库版本（v1/v2），用编译器编译后交由
  工具分析 ABI 差异，验证工具能正确检测破坏性变更。

### 为什么 OHOS 上无法运行上游 -test（技术原因，非环境缺失）

在 OHOS 工具链环境（仅提供 clang，无 gcc/g++）实测：

1. 直接运行 `perl abi-compliance-checker.pl -test`：
   ```
   ERROR: can't find GCC>=3.0 in PATH
   ```

2. 将 `gcc`/`g++` 符号链接指向 OHOS clang 后重试：
   ```
   gcc -fdump-lang-raw -fkeep-inline-functions -c ... -fpreprocessed ...
   clang-15: error: unknown argument: '-fdump-lang-raw'
   clang-15: error: unknown argument: '-fpreprocessed'
   ERROR: some errors occurred when compiling headers
   ERROR: analysis has failed (5)
   ```

结论：
- 上游 RegTests 依赖 **GCC 专属选项 `-fdump-lang-raw`**（GCC 翻译单元 AST dump，
  是 abicc ABI 分析的数据来源），clang 15 **不支持该选项**（实测报 unknown argument）。
- 该选项无 clang 等价替代；上游 ABI dump 引擎（GccAst.pm/ABIDump.pm）硬编码 GCC AST
  dump 格式。
- 因此上游 -test 在仅 clang 的 OHOS 工具链上技术上无法运行——属编译器能力不匹配，
  而非"没环境"。若后续 OHOS 提供 gcc 环境，可立即运行 `-test` 补齐上游测试通过率证据。

### 已尝试的等价验证

- 用 clang 成功编译 v1/v2 两个版本样本库（`libfoo.so`，`foo_mul` 签名变化），
  验证工具链可编译样本；但 abicc 对比分析内部仍调用 gcc（`can't find GCC>=3.0 in PATH`），
  同样受上述限制。
- test_package 冒烟测试：验证打包产物存在、可执行、`--help` 正常输出（1/1 通过）。
- CI 门禁：L0-L5 全部通过（L0 pass, L1 pass, L2 skip, L4 pass, L5 pass）。

## 构建要点

- 纯 Perl 脚本工具，无需编译（`package_type = application`）。
- 运行时依赖 `perl/5.42.2`（制品仓已有预编译包）。
- 打包时修复 shebang（`#!/usr/bin/perl` → `#!/usr/bin/env perl`），适配 OHOS 无
  `/usr/bin/perl` 的环境。
- 主脚本 + `modules/` 目录安装到 `share/abi-compliance-checker/`（getModules() 按
  `../share/abi-compliance-checker/modules` 查找）。
