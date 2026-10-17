# rats 2.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-29
- 编译器: clang/clang++
- 状态: built

## 编译步骤

RATS 使用老式 autotools 构建，上游已生成 `configure` + `Makefile.in`（无 `Makefile.am`，构建期
不需要 automake）；lexers 已预生成为 `lex.yy*.c`，不需要 flex。

适配时在 `generate()` 注入 `AutotoolsDeps` + `VirtualBuildEnv` + `AutotoolsToolchain`，并把
expat 的 include 目录并入 `CFLAGS`（因 `Makefile.in` 编译规则只用 `$(CFLAGS)`、不引用
`$(CPPFLAGS)`）。`build()` 经 `/system/bin/sh` 运行 `configure`，显式
`--host=aarch64-unknown-linux-ohos --build=x86_64-pc-linux-gnu` 强制交叉模式，并在末尾追加
`--prefix={package_folder}` 覆盖工具链注入的 `/`。随后 `make -j1` 与 `make install` 均在
`source_folder` 内执行（`Makefile.in` 无 VPATH，不能 out-of-tree 构建）。`package()` 阶段对
`bin/rats` 做 OHOS ELF 自签（`binary-sign-tool sign -selfSign 1`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot run C compiled programs` | conan-verify 用 `-pr:b == -pr:h == ohos-aarch64`，autoconf 试图运行探针 ELF | 显式 `--host/--build` 强制 cross 模式 |
| 2 | `make: No rule to make target 'engine.o'` | `Makefile.in` 无 VPATH | 改为 in-tree 构建 |
| 3 | `vuln_db.c: fatal error: 'expat.h' file not found` | 编译只用 `CFLAGS` 不引用 `CPPFLAGS` | expat include 目录并入 `CFLAGS` |
| 4 | `make install` 写 `//bin` Permission denied | `AutotoolsToolchain` 注入 `--prefix=/` | 末尾显式 `--prefix={package_folder}` 覆盖 |

## 源码修改

无补丁（路径 A 基础适配）。

## 依赖版本

- expat/2.8.4

## 验证结果

conan-verify 8 道门禁全部通过（G1/G0/G2/G3/G4/L2/L4/L5）。test_package 端到端运行 `rats` 审计
不安全样本，命中 `High: fixed size local buffer` / `High: strcpy`；干净样本无 High/Medium。
共 N=3 条消费者断言全部通过。

## 注意事项

- 上游 `--help` 调用 `usage(); exit(1)`，退出码为 1（非 0），测试脚本只校验输出内容、不卡退出码。
- 安装后二进制通过 `package_info` 把 expat 的 libdir 注入 `LD_LIBRARY_PATH`，以定位 `libexpat.so`。

---
**编译结束**: 2026-09-29
**最终状态**: built
