# runit 2.3.1 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-15
- 编译器: clang/llvm-ar
- 状态: built

## 编译步骤

1. `init-build runit 2.3.1 --url=https://smarden.org/runit/runit-2.3.1.tar.gz` 下载并解压源码。
2. 编写 Conan 配方，在 `source()` 中将上游 `runit-2.3.1/src` 提升为实际构建目录。
3. 在 `build()` 中根据 Conan profile 写入 `conf-cc`、`conf-ld`、`conf-ar`，使用 `make -j1` 构建。
4. 在 `package()` 中安装 `chpst`、`runit`、`runit-init`、`runsv`、`runsvchdir`、`runsvdir`、`sv`、`svlogd`、`utmpset` 以及 man8 手册。
5. 使用 `finish runit 2.3.1 built` 执行 conan-verify 与 W3 本地 CI。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 默认 `conf-cc`/`conf-ld` 使用 gcc | OHOS profile 提供 clang，不保证有 gcc/cc 入口 | recipe 中按 Conan `tools.build:compiler_executables` 写入 clang/llvm-ar |
| 2 | `make -j` jobserver mkfifo 失败 | HMDFS/TMPDIR 对 FIFO 创建有限制 | 固定使用 `make -j1` |
| 3 | 上游源码目录嵌套在 `runit-2.3.1/src` | tarball 顶层不是直接构建目录 | `source()` 中自动提升 src 内容 |

## 源码修改

无持久源码补丁。工具链配置由 Conan recipe 在构建目录中生成，不修改上游源码。

## 依赖版本

无第三方 Conan 依赖。

## 验证结果

```bash
python3 scripts/ohc-run.py finish runit 2.3.1 built
# conan-verify: PASS
# W3 local CI: PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 构建配方 |
| conandata.yml | 上游源码 URL 与 SHA256 |
| test_package/conanfile.py | 消费者视角 smoke test |
| commands.json | 命令行工具声明 |

## 注意事项

runit 是命令行工具集合，软件级 `commands.json` 必须随配方一起提交。
---

**编译结束**: 2026-07-15 03:39
**最终状态**: built
