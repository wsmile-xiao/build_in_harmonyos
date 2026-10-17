# bpftrace-tools 0.26.1 适配笔记

## 编译环境
- 构建系统: custom（纯脚本拷贝，无编译）
- 编译日期: 2026-09-07
- 编译器: clang/clang++（无实际编译，仅占位）
- 状态: published

## 编译步骤

bpftrace 本体为 C++20 + LLVM + libbpf 的重型项目，依赖链（LLVM>=21、libbpf、bcc、libelf、zlib）在制品仓未发布，无法在 OHOS aarch64 上完整编译。`bpftrace-tools` 为仓库 `tools/` 目录下的精选 `.bt` 脚本集合，Alpine 等发行版已将其拆分为独立子包 `bpftrace-tools`（32 KiB，112 KiB 安装后）。本次适配回归该分包策略：仅分发脚本资源，不编译二进制。

步骤：
1. `get()` 下载 `https://github.com/bpftrace/bpftrace/archive/refs/tags/v0.26.1.tar.gz`，`strip_root=True` 去顶层目录。
2. `package()` 将 `tools/*.bt` 拷贝至 `share/bpftrace/tools/`，`tools/old/*.bt` 拷贝至 `share/bpftrace/tools/old/`，`tools/README.md` 与 `LICENSE` 拷贝至对应位置。
3. `package_id()` 清空，保证单一 package_id；`package_info()` 清空 bindirs/libdirs/includedirs，通过 `runenv_info` 暴露 `BPFTRACE_TOOLS_PATH`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 若尝试完整编译 bpftrace，需 LLVM 21、libbpf、bcc 等制品仓缺失依赖 | 依赖未发布（R36） | 仅打包 tools 脚本，避免引入未发布依赖；如需完整 bpftrace 二进制，需先发布 llvm/libbpf/bcc 依赖链 |
| 2 | CI L5 制品检查对 `bin/`/`lib/` 的期望 | 纯数据包无 bin/lib | 保留 `share/bpftrace/tools` 为制品，L5 允许 warn；若后续需要命令行包装，可在 `bin/` 添加 wrapper 并补 `commands.json`（R38） |
| 3 | 上游无针对 tools 的独立测试套件 | tools 为 .bt 观测脚本，测试依赖内核 BPF | 在 test_package 中做离线静态校验（数量、探针语法、README 存在），并在 MANIFEST 中声明 `upstream_tests_exist: false` + 审计说明 |

## 源码修改

无补丁。

## 依赖版本

无运行时依赖。

## 验证结果

本地预校验（拟在真机执行）：
```bash
conan create archives/b/bpftrace-tools/0.26.1 --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
预期：
- `conan create` 成功，日志含 `Testing package`
- test_package 执行：校验工具数 >=30，核心工具 `opensnoop.bt`/`execsnoop.bt`/`biolatency.bt` 存在且含探针关键字
- `HMBS_TEST_PACKAGE_RESULT` 与 `HMBS_UPSTREAM_TEST_RESULT` 标记正常输出

## 交付物

| 文件 | 说明 |
|------|------|
| share/bpftrace/tools/*.bt | 主工具脚本（>35 个） |
| share/bpftrace/tools/old/*.bt | 兼容旧内核的旧版脚本 |
| share/bpftrace/tools/README.md | 工具说明 |
| licenses/LICENSE | Apache-2.0 |

## 注意事项

- 工具运行需内核 eBPF + bpftrace 二进制，OHOS 当前内核未启用 BPF 相关配置，工具仅作脚本资源分发与静态校验，不在测试阶段实际挂载探针。
- 如后续补齐 bpftrace 二进制，应新增 `bpftrace/0.26.1` 配方并让 `bpftrace-tools` 通过 `requires` 依赖它，保持与 Alpine 拆包语义一致。
