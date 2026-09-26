# nanomsgxx 0.2 适配笔记

## 软件简介

nanomsgxx 是 nanomsg 的简单 C++11 绑定库，提供 `nnxx::socket`、`nnxx::message` 等类型安全的封装，支持 SP/PAIR/REQ/REP/PUB/SUB/SURVEY/BUS 等可扩展消息模式。纯头文件 + 单个静态/共享库 `libnnxx`，依赖 `nanomsg`。

## 编译环境

- 构建系统: waf（上游 0.2 打包 waf 1.7.11 → 替换为 py3 兼容 waf 2.0.22）
- 编译日期: 2026-09-19
- 编译器: clang/clang++（OHOS aarch64，profile tools.build:compiler_executables）
- 依赖: nanomsg/1.2（conan 制品仓已发布）
- 状态: built（conan-verify 判定可发布；PR 合并后由 CI release 上传更新为 published）

## 编译步骤

```bash
# waf 2.0.22 替换上游 1.7.11 后（conanfile.py source() 自动下载，Homebrew 同款
# 提交 4426567809 的 waf，sha256 校验 + VERSION 探针校验）
python3 waf configure --prefix=/ --libdir=/lib --nodoc --nopkgconfig
python3 waf build
python3 waf --alltests     # 上游 14 个单元测试 14/14 通过
python3 waf install --destdir=<pkg>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游打包 waf 1.7.11 在 py3 下无法运行（py2 时代二进制+py2 语法） | 2016 年老 waf 仅支持 Python 2 | 替换为 py3 兼容 waf 2.0.22（Homebrew nanomsgxx.rb 公式同款来源，sha256 一致，确保官方可复现） |
| 2 | `src/nnxx/wscript` 的 `print cmd` 是 py2 语法，py3 报 SyntaxError | py2 时代 waf 脚本 | 补丁 `0001-nnxx-wscript-py3.patch`：`print cmd` → `print(cmd)` |
| 3 | waf 2.x 下 tests 目标报 "source not found" | waf 2.x 的 `waf.path.ant_glob('*.cpp')` 返回虚拟节点，需转相对路径 | 补丁 `0002-tests-wscript-newer-waf.patch`：`f = f.path_from(waf.path)`（上游 commit 08c6d88 / PR#13 官方修复） |
| 4 | waf configure 找不到 clang | waf 不自动读取 profile 的 [buildenv] PATH | conanfile.py generate() 用 VirtualBuildEnv + `_build_env()` 注入 CC/CXX/AR/RANLIB（来自 `tools.build:compiler_executables`）与 nanomsg 头/库路径（R33：禁止裸用 shell 变量） |
| 5 | `waf --run_tests` 报 "no such option" | waf 2.x 用 `--alltests` 运行单元测试（`--run_tests` 是旧版选项） | 改用 `waf --alltests`，测试二进制运行时注入 LD_LIBRARY_PATH |
| 6 | test_package 编译报 `nanomsg/bus.h not found` | nnxx 头文件内部 `#include <nanomsg/...>`，需传递依赖头路径 | test_package 从 `self.dependencies` 全图收集 include/lib 路径后编译 |
| 7 | 独立消费者用例 REQ/REP 回环 | 需遵守 nanomsg REQ 状态机（应答前不能重复 send）、REP 按序 recv→send | consumers/nnxx_reqrep_consumer.cpp 实现完整请求-应答回环，真机实测 PASS（consumer PASS: REQ/REP 回环 'ping?' -> 'pong!' over inproc://） |

## 源码修改

| 补丁 | 修改内容 |
|------|----------|
| `0001-nnxx-wscript-py3.patch` | `src/nnxx/wscript` print cmd → print(cmd)（Python 3 兼容） |
| `0002-tests-wscript-newer-waf.patch` | `tests/wscript` 增加 `f = f.path_from(waf.path)`（waf 2.x 目标解析修复，上游官方 PR#13） |

> 未修改任何 C++ 源文件 —— 适配仅围绕构建系统（waf 版本 + 脚本 py3 化）。平台适配主要依赖 nanomsg 依赖本身已适配 OHOS + clang OHOS target。

## 依赖版本

- nanomsg/1.2（harmonyos 适配版，已发布制品仓）

## 验证结果

```bash
# conan create 完整验证（configure + build + 上游测试 + install + test_package）
conan create archives/n/nanomsgxx/0.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=<同> --build=missing --build="nanomsgxx/*" --user=ohpcd --channel=stable

# 上游单元测试（waf --alltests，并入 conan create 的 build()）
execution summary
  tests that pass 14/14
  tests that fail 0/14

# test_package 消费者测试
RUN: .../test_nanomsgxx
test_nanomsgxx: PASS (round-trip 'nanomsgxx test payload' over inproc://)
```

- G0/G1/G2/G3/G4 + L2/L4/L5 门禁全部 PASS，conan-verify 判定 `published` 可发布。

## 知识沉淀

- 老包内嵌 py2 构建引导脚本（waf 1.7.11）的适配范式：替换为 py3 兼容 waf 2.x（Homebrew formula 同款来源保证官方可复现），而非放弃该构建系统。
- waf 2.x 的 tests/wscript 目标解析需 `f.path_from(waf.path)`（上游 PR#13）。
- 本包为纯库（libnnxx + 头文件），无命令行工具 → 不需要 commands.json（R38）。
---

**编译结束**: 2026-09-19 20:44
**最终状态**: built
