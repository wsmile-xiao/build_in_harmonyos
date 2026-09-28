# postmark 1.53 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，单目标 `make CC=clang -j1 postmark`，无 configure）
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 上游源码为单文件 C（postmark-1.53.c + Makefile + postmark.1），14KB tarball
# 构建命令（conan 配方内）：
make CC=clang -j1 postmark
# 产物：postmark 可执行文件（CLI 基准工具）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接失败 `undefined symbol: getwd` | `getwd()` 为废弃 POSIX API（XPG/BSD 遗留），OHOS bionic libc 无此符号；源码 `#else` 分支使用 `extern char *getwd()` | 改用标准 `getcwd(x, MAX_LINE)`（与 `#ifdef _WIN32` 分支一致），并补充 `#include <unistd.h>`（patches/0001-postmark-1.53.c.patch） |
| 2 | 编译大量 deprecated 警告 | 源码为 1997-2001 年 ANSI C 风格（无原型函数定义等），clang 默认仅警告 | 非致命，不启用 -Werror，仅记录 |
| 3 | test_package 首次断言失败 | postmark 报告格式无 "Transactions: N" 行，事务数以 "per second" 形式输出 | test.sh 断言改为模式匹配 `transactions ([1-9][0-9]* per second)` + `Files:` 块 + exit 0（消除对字面量 10 的时序敏感） |
| 4 | test_package "out of files!" | 测试配置文件数(2) < 事务数(10)，postmark 工作负载要求文件数多于事务数 | 文件数改为 20（> 事务数 10） |

## 源码修改

补丁文件：patches/0001-postmark-1.53.c.patch
- 删除 `extern char *getwd();` 声明
- `#define GETWD(x) getwd(x)` → `#define GETWD(x) getcwd(x,MAX_LINE)`（#else 分支）
- 增加 `#include <unistd.h>`

## 依赖版本

无外部依赖（仅标准 C 库：stdio/string/stdlib/time/fcntl/unistd）

## 验证结果

```bash
# conan-verify（G1-G4 + L2/L4/L5 全部 PASS）
# W3 本地 CI 模拟（build_and_test.sh）通过
# test_package 端到端：postmark 完整 benchmark 运行（2 文件→20 文件/10 事务），4 项断言全部通过
$ bash test_package/test.sh
--- postmark consumer verification ---
PASS 1: banner printed
PASS 2: report contains transaction summary
PASS 3: report contains Files block
PASS 4: postmark exit code 0
test postmark 1.53: 4/4 checks PASS
```

## 注意事项

1. 上游为 NetApp PostMark 磁盘 I/O 基准工具（1997-2001），官方 SLAC 网页源已从互联网消失；本配方采用 Debian 权威快照源（snapshot.debian.org orig tarball），sha256 已实测固化
2. License: Artistic License（源码内含全文）+ GPL-2+（Debian 打包元数据）
3. 本机裸 clang 直接链接报 lld 加载 libxml2 符号错误（环境问题），conan create 独立 toolchain 验证不受影响
4. JC 全仓扫描误拦历史残留（cloog/kics 状态文件）问题：CI 实际使用 PR diff 模式（pr.diff），仅检查 PR 涉及文件，不受历史残留影响；本地 W3 在功能分支上以 incremental 模式（git diff origin/main...HEAD）验证通过

---

**编译结束**: 2026-09-26 16:02
**最终状态**: built
