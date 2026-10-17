# qprint 1.1.dfsg.2 适配笔记

## 软件信息

- 上游: <https://www.fourmilab.ch/webtools/qprint/>（John Walker；
  quoted-printable 编码/解码 CLI，RFC 1521；单文件 C 985 行 + 自带 getopt）
- 版本: 1.1.dfsg.2（Debian orig tarball 为规范分发源；dfsg 仅剔除文档资源）
- 任务: ohpcd（领取时无人认领、无 PR 记录、仓库未收录）

## 编译环境

- 真机: 10.195.180.238（隔离 job `device-b/qprint-kb-20260920`）
- 构建系统: autotools（tarball 自带 configure+Makefile.in，无需 autoreconf）
- 状态: built

## 上游测试清点（R51 第 1 步）

| 清点项 | 结果 | 依据 |
|---|---|---|
| tests/ 目录 | 不存在 | 解包清单 |
| make check/test 目标 | 无 | Makefile.in 仅 all/install/clean |
| 上游测试 | **0 个** | CLI 工具零测试；消费者往返为唯一验证 |

## 验证结果（真机实测）

- conan create: 退出码 0
- 消费者: **2/2 通过**（roundtrip: OK + known-value: OK）
- 产物: bin/qprint（CLI，commands.json 已按 R38 声明）

## CI 回归修复（2026-09-24）

- CI #59789 暴露 `0002-Makefile-in-installdirs.patch` 为损坏的 unified diff；已按 Debian `Makefile.in` 实际上下文重生成，并通过 `git apply --check`。
- 真机复测：补丁应用、clang 交叉编译、`make install DESTDIR` 及 consumer 均通过；`bin/qprint`、`share/man/man1/qprint.1` 均生成。
- `test_package/test.sh` 统一为 LF，避免 HarmonyOS `/bin/sh` 将 CRLF 的 `set -eu` 解析为非法选项。

## 注意事项

- PR 前缀【知识库扩展】；分支 feat/qprint-1.1.dfsg.2
- CLI 工具：软件级 commands.json（archives/q/qprint/commands.json）必填（R38/L0k）
