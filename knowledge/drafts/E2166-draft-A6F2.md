# E2166 — 混合语言 Automake 测试须分别绑定实际展开的测试驱动入口

## 错误特征

项目同时包含 C 测试、Perl 脚本与 YAML 规格测试。`make check` 首个 C 测试可能停在 `binaryload_event_call`，或修复 C 测试后 `.pl`、`.yaml` 用例仍大量 FAIL。只设置 `LOG_COMPILER` 时，日志里的实际命令完全没有使用它。

## 触发条件

- 构建系统：Automake `parallel-tests`，并包含多种测试扩展名或测试脚本内部启动的子程序。
- 阶段：上游 `make check`；在部分文件系统上，Libtool 生成的无扩展名 shell wrapper 不能直接启动。

## 根因分析

Automake 的默认变量名称不一定是生成后的有效入口。发布包中的 `tests/Makefile.in` 可以明确写出 `LOG_COMPILE = $(WINE)`，因此覆盖 `LOG_COMPILER` 不会改变 C 测试命令；`.yaml` 规则另用 `YAML_LOG_COMPILER`。而 Perl 用例里直接调用 `../tools/<name>` 时，会绕过两种 Automake launcher。单一入口的修复不能外推为所有测试已可执行。

这与 E228 的“辨认 Libtool wrapper 与直接 ELF”不同：本条处理的是多个测试驱动的覆盖边界；与 E259 的 `NDEBUG` 断言副作用也不同。遇到 YAML 解析失败时还需独立检查 Release 构建是否省略了初始化调用，不能把解析错误当作驱动变量问题。

## 解决方案

### 推荐方案

1. 阅读发布包生成的 `Makefile.in` 及配置后的 `Makefile`，列出 C、脚本、自定义扩展名各自使用的 `LOG_COMPILE`、`*_LOG_COMPILER` 和内部子进程调用。
2. C 测试通过 `LOG_COMPILE` 指向条件 launcher：仅检测到相邻 `.libs/<basename>` 时用 shell 解释外层 wrapper；直接 ELF 原样执行。
3. 给自定义扩展名提供等价语义的专用 launcher，保留原环境设置与输入；脚本内部直接调用的 Libtool wrapper 用最小源码补丁显式交给 shell。
4. 保留每项测试的退出码、原断言与完整 `TESTS` 分母，用 `.trs` 逐项记录及 `test-suite.log` 的 N/N 汇总复核。

### 禁止做法

- 不要因为 `LOG_COMPILER` 被接受为命令行变量就假定它实际生效；要核对生成规则。
- 不要把直接 ELF 统一交给 shell，或删除 `.pl`、`.yaml` 用例来凑通过率。
- 不要把测试驱动问题与 Release `NDEBUG` 导致的应用逻辑缺陷混为一谈。

## 验证

liblouis 3.38.0 的失败轮次分别证明 `LOG_COMPILER` 未被读取、Perl 内部 wrapper 调用及 YAML 独立驱动未被 C launcher 覆盖。修复后，OpenHarmony PC 单次 W3 事务 `liblouis-w3-20260925T152815Z` 的原生上游测试为 209/209 PASS、0 SKIP、0 FAIL，安装后消费者测试为 1/1 PASS；测试汇总 SHA-256 为 `f6a527b328554088262be7cd8875237747805527373e2c2fc3235b663bfae213`。

## 适用边界与关联

只在生成规则确实使用这些变量时覆盖它们；其他扩展名须按其自身规则确认。E228 描述如何区分 Libtool wrapper 与 ELF，E259 描述 `assert` 中副作用在 `-DNDEBUG` 下被移除；两者不能替代本条的多入口盘点。
