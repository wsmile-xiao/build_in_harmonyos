# cht.sh 0.0-git20220418.571377f 适配笔记

## 软件说明

cht.sh 是 [cheat.sh](https://cheat.sh) 服务的命令行客户端（纯 bash
脚本）：shell 模式、查询历史、剪贴板集成、stealth 模式、tab 补全。
无编译步骤，Debian 打包架构为 `all`。

> 立项时任务清单标注为 C++，经核实（Debian .dsc、上游 tarball 文件
> 类型统计：43 .py / 0 个 C++ 源文件）确认为 Python/Shell 项目，用户已
> 确认按应用类适配。

## 编译环境
- 构建系统: 无（纯脚本安装）
- 编译日期: 2026-09-10
- 编译器: 无
- 状态: pending

## 编译步骤

1. 下载源码（Debian orig tarball，sha256 已与 .dsc 校验一致）
2. 按 Debian 官方 rules 安装 4 个文件（package() 内 copy/rename/chmod）：
   - `share/cht.sh.txt` → `bin/cht.sh`（755）
   - `share/bash_completion.txt` → `share/bash-completion/completions/cht.sh`（644）
   - `share/fish.txt` → `share/fish/vendor_completions.d/cht.sh.fish`（644）
   - `share/zsh.txt` → `share/zsh/site-functions/_cht.sh`（644）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 仓库 chts/cht.sh 404 | 上游实际仓库是 chubin/cheat.sh，版本号 0.0-git20220418.571377f 对应 Debian 源包 | 用 deb.debian.org pool 的 orig tarball，sha256 经 .dsc 校验 |
| 2 | 脚本 shebang `#!/bin/bash`，OHOS 无 /bin/bash | OHOS 的 bash 在 $PATH 而非 /bin | 测试经 `bash <script>` 显式调用，不依赖 shebang 路径 |

## 依赖版本

无构建依赖。运行时依赖：curl（必需）、rlwrap（shell 模式）、xsel（剪贴板）。

## 测试

上游 tests/ 目录为手动测试结果快照（16/19/22/24/25 号 sheet），无可执行
测试框架 → test_package 补全：

- 断言 1：bin/cht.sh 已安装
- 断言 2：`bash -n` 语法检查通过
- 断言 3：`cht.sh --help` 退出码 0 且输出含 Usage（该分支在 rlwrap/mktemp
  依赖检查之前 exit 0，无运行时依赖；本机实测 rc=0）
- 断言 4：3 个 shell 补全文件已安装

共 4 项断言，本地 `conan create` 验证（见 reports/）。

## 注意事项

- 本机 /bin/sh 为 zsh 且 /tmp 只读：test.sh 避免 here-document
- 查询功能（`cht.sh tar` 等）需网络 + curl，属 L2 以上集成测试，不在 CI L1 范围
