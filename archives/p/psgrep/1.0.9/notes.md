# psgrep 1.0.9 适配笔记

## 编译环境
- 构建系统: custom（纯 Bash 脚本，无编译步骤）
- 编译日期: 2026-07-14
- 编译器: N/A
- 状态: built

## 编译/打包步骤
1. 下载上游源码包 `1.0.9.tar.gz`。
2. 校验 SHA256: `6408e4fc99414367ad08bfbeda6aa86400985efe1ccb1a1f00f294f86dd8b984`。
3. 应用 Conan patches（当前无补丁）。
4. 执行上游 `install.sh` dry-run 语法检查作为上游测试替代。
5. 复制 `psgrep` 到 Conan package `bin/`。
6. 复制 `psgrep.1` 到 Conan package `share/man/man1/`。
7. test_package 运行 `psgrep -h`、`psgrep -v`、`psgrep -n -s`、`psgrep -d`，校验帮助、版本和真实进程搜索输出。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `psgrep -v` 返回非零退出码 | 上游 `version_info()` 打印版本后 `exit 2` | 测试中捕获返回码并要求等于 2，同时校验输出包含 `psgrep version 1.0.9` |
| 2 | 项目无 `make check` 或测试目录 | 上游只提供 Bash 脚本和 install.sh | build 阶段执行 `bash -n psgrep install.sh` 与 `install.sh -h` 行为检查；消费者测试执行真实 CLI 功能 |
| 3 | GitHub 直连下载超时 | 当前网络无法连接 github.com:443 | 校验时使用 ghproxy.net 镜像获取同一上游 tarball；配方保留官方 URL |

## 依赖版本
- 编译依赖: 无
- Conan 依赖: 无
- 运行时系统命令: bash, ps, grep, awk, head, which

## 测试质量说明
- 上游测试: 无官方测试套件；以 Bash 语法检查、install.sh 参数校验和消费者 CLI 功能测试覆盖。
- 消费者测试: 真实执行安装后的 `psgrep`，校验帮助文本、版本文本、简化格式搜索和 PID-only 搜索。
- 断言数: 8

## 注意事项
1. 本包为纯脚本工具包，无静态/动态库，`cpp_info.libs = []`。
2. `settings` 仅保留 `os`、`arch`，避免对编译器/构建类型产生无意义包 ID。
3. 软件级 `commands.json` 已创建，满足工具包 R38/L0k 要求。
4. 上游脚本已使用 `#!/usr/bin/env bash`，无需 shebang 补丁。
