# 上游测试双口径台账 — dict 1.13.3

## 测试入口枚举（源码声明）

上游测试入口为 `make test`（Makefile.in: `test: $(EXES) $(LIBRARIES); cd test && sh dictd_test && sh dictzip_test`），
全部为 shell 脚本驱动，无 CTest/GTest/自定义注册机制。逐项枚举如下：

### A. dictd_test — DICTFMT 段（dictfmt 词典格式化与索引生成，21 项）

| # | 用例 | 类型 | 命令 |
|---|------|------|------|
| 1 | `-c5 == -t` 等价性 | 基础断言 | `printf "   -c5 == -t ..."` + cmp |
| 2 | `-c5.utf8` UTF-8 输出 | 基础断言 | cmp_2_files |
| 3 | `-c5 == -X` 等价性 | 基础断言 | cmp |
| 4 | `c5 == e` 等价性 | 基础断言 | cmp |
| 5 | `c5 == f` 等价性 | 基础断言 | cmp |
| 6 | `c5 == j` 等价性 | 基础断言 | cmp |
| 7 | `c5 == p` 等价性 | 基础断言 | cmp |
| 8 | `c5 == expected` 与 db.expect 比对 | 基础断言 | cmp_2_files + cmp_index_files |
| 9-13 | smiley_1..smiley_5 词典构建 | db 测试 | dictfmt + cmp_2_files/cmp_index_files |
| 14-18 | hello_1..hello_5 词典构建 | db 测试 | dictfmt + cmp |
| 19 | cyrillic_1 词典构建 | db 测试 | dictfmt + cmp |
| 20 | mixedcase_1 词典构建 | db 测试 | dictfmt + cmp |
| 21 | indexdata_1 词典构建 | db 测试 | dictfmt + cmp |

### B. dictd_test — DICTD 段（dictd 服务器协议应答，17 项）

| # | 用例 | 类型 | 命令 |
|---|------|------|------|
| 1 | hello_1 协议应答 | server 用例 | dictd + dict + cmp 期望文件 |
| 2 | hello_2 协议应答 | server 用例 | 同上 |
| 3 | hello_3 协议应答 | server 用例 | 同上 |
| 4 | hello_4 协议应答 | server 用例 | 同上 |
| 5 | hello_5 协议应答 | server 用例 | 同上 |
| 6 | smiley_2 协议应答 | server 用例 | 同上 |
| 7 | smiley_4 协议应答 | server 用例 | 同上 |
| 8 | smiley_5 协议应答 | server 用例 | 同上 |
| 9 | cyrillic_1 协议应答 | server 用例 | 同上 |
| 10 | cyrillic_1 nodetach nofork（绑定 localhost:26281） | server 用例 | dictd_test_daemon + dict -h localhost |
| 11 | cyrillic_3 协议应答 | server 用例 | 同上 |
| 12 | cyrillic_4 协议应答 | server 用例 | 同上 |
| 13 | mixedcase_1 协议应答 | server 用例 | 同上 |
| 14 | indexdata_1 协议应答 | server 用例 | 同上 |
| 15 | limits_1 协议应答 | server 用例 | 同上 |
| 16 | defstrat_1 协议应答 | server 用例 | 同上 |
| 17 | defstrat_2 协议应答 | server 用例 | 同上 |

### C. dictzip_test — dictzip 压缩/随机访问解压（9 项）

| # | 用例（bytes × step） | 类型 |
|---|------|------|
| 1 | 116630 × 11663 | 压缩 + 区域解压 |
| 2 | 1000000 × 500000 | 压缩 + 区域解压 |
| 3 | 100000 × 25000 | 压缩 + 区域解压 |
| 4 | 10000 × 250 | 压缩 + 区域解压 |
| 5 | 0 × 1 | 压缩 + 区域解压 |
| 6 | 1 × 1 | 压缩 + 区域解压 |
| 7 | 10 × 1 | 压缩 + 区域解压 |
| 8 | 100 × 1 | 压缩 + 区域解压 |
| 9 | 1000 × 25 | 压缩 + 区域解压 |

## 双口径统计

| 口径 | 数量 |
|------|------|
| source_declared_total（源码声明总数） | 47（DICTFMT 21 + DICTD 17 + dictzip 9） |
| configured_executable_total（当前 OHOS 配置实例化可执行数） | 47（全量 shell 脚本驱动，无互斥编译分支/条件宏/类型实例化/禁用条件） |
| executed_passed_total（实际执行并通过） | 47 |
| failed_total | 0 |
| uninstantiated_total | 0 |
| 全量通过率 | 47/47 (100%) |

### 口径映射（源码声明 → 构建条件 → 构建目标 → 注册项 → 执行日志）

- 声明/注册项：`test/dictd_test`（DICTFMT 21 + DICTD 17 项）、`test/dictzip_test`（9 项），由 Makefile.in `test:` 目标 `cd test && sh dictd_test && sh dictzip_test` 注册。
- 预处理/构建条件：脚本测试无 C 级条件宏；执行依赖 `dict`、`dictd`、`dictzip`、`dictfmt` 可执行产物（Makefile `$(EXES)`），全部构建。
- 构建目标：`make test`（依赖 EXES + LIBRARIES）。
- 注册项：无 ctest -N / GTest 注册（纯 shell 脚本，无框架）。
- 实际执行日志：`reports/conan-create.log`（conan create 内 `make test` 段，第 331-375 行，40 个 passed 标记 + DICTZIP 9 段全部执行），SHA-256 见 final 报告。

## 结论

上游 47 项测试在 OHOS aarch64（os=OHOS, clang 15, libc++）配置下全部实际运行并通过（100%），
与先例 dictd/1.13.3 的 `make test` 结论一致；无未实例化、无跳过、无硬阻塞项。
