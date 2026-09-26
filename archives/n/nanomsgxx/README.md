# nanomsgxx

## 简介

nanomsgxx 是 [nanomsg](https://nanomsg.org/) 的简单 C++11 绑定库，提供类型安全的 `nnxx::socket`、`nnxx::message`、`nnxx::poll` 等接口封装，支持 PAIR、REQ/REP、PUB/SUB、PUSH/PULL、SURVEY、BUS 等可扩展消息模式，以及 inproc/tcp/ipc 传输。

- 上游仓库: https://github.com/achille-roussel/nanomsgxx
- 协议: MIT License
- 依赖: nanomsg/1.2

## OHOS 适配

### 适配要点
- **waf 1.7.11 → 2.0.22**：上游 0.2 打包的是 Python 2 时代 waf 1.7.11（py3 下不可运行），替换为 py3 兼容 waf 2.0.22。来源与 Homebrew `nanomsgxx.rb` 公式一致（上游 master 提交 `4426567809` 的 waf，sha256 校验 + VERSION 探针双保险），保证官方可复现。
- **wscript py3 化**：`src/nnxx/wscript` 的 `print cmd` 改为 `print(cmd)`（补丁 0001）。
- **waf 2.x 测试目标解析**：`tests/wscript` 增加 `f = f.path_from(waf.path)`（上游官方 commit `08c6d88` / PR#13，补丁 0002）。
- **工具链注入**：waf 运行时通过 conanfile 注入 `CC/CXX/AR/RANLIB`（来自 profile `tools.build:compiler_executables`）与 nanomsg 依赖头/库路径（来自依赖包 `cpp_info`），满足 R33。

### 测试
- 上游单元测试（waf `--alltests`）**14/14 通过**，随 conan create 的 build() 阶段自动执行。
- test_package 消费者级测试 `test_nanomsgxx.cpp` 真实验证 inproc:// PAIR 消息回环（R34）。

### 补丁列表
1. `0001-nnxx-wscript-py3.patch`：`src/nnxx/wscript` Python 3 语法兼容
2. `0002-tests-wscript-newer-waf.patch`：`tests/wscript` waf 2.x 目标解析修复（上游 PR#13）

## 已知问题
- 无（waf 构建适配完整，无功能裁剪）。

## 版本
| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 0.2 | published | 2026-09-19 | 首次适配，依赖 nanomsg/1.2 |
