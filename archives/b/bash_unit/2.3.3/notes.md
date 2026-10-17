# bash_unit 2.3.3 适配笔记

## 编译环境

- 构建系统：custom（纯 Bash 脚本，无编译步骤）
- 编译日期：2026-08-25
- 运行时：HarmonyOS Bash `/data/service/hnp/bin/bash`
- 状态：built

## 构建与打包

源码中的 `bash_unit` 可执行脚本直接安装到 Conan 包的 `bin/`，许可证和文档分别安装到 `licenses/` 与 `share/doc/bash_unit/`。配方无第三方 Conan 依赖。

## 平台兼容问题

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `notify_message` 失败 | HarmonyOS toybox `sed` 不支持 GNU `sed -u` | 删除非必要的 `-u` 参数 |
| 2 | 文档测试无法写入 `/tmp` | HarmonyOS `/tmp` 只读 | 使用 `${TMPDIR:-/tmp}` 创建测试临时目录 |
| 3 | 文档测试的 sed 地址语法失败 | toybox `sed` 不支持上游脚本使用的 GNU 地址写法 | 使用等价 `awk` 逻辑提取文档测试块 |
| 4 | Linux/Darwin 平台示例误运行 | `uname` 返回 `HarmonyOS` | 在平台跳过条件中显式处理 HarmonyOS |

## 测试结果

完整保留并执行上游四个测试入口：

```bash
TMPDIR=/storage/Users/currentUser/tmp/bash-unit-test \
  FORCE_COLOR=false ./bash_unit tests/test*
```

结果：`tests/test_cli.sh`、`tests/test_core.sh`、`tests/test_doc.sh`、`tests/test_tap_format` 全部通过。消费者测试另外调用 Conan 包中的 `bash_unit`，运行两个真实断言并检查 `SUCCESS` 输出。

## 依赖

无第三方 Conan 依赖。运行时需要 Bash 和基础 Unix 命令（awk、grep、find、mktemp、sort 等）。
---

**编译结束**: 2026-08-25 22:01
**最终状态**: built
