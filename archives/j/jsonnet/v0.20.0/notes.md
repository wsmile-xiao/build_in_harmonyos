# jsonnet v0.20.0 适配笔记

## 编译环境
- 构建系统: Makefile（纯 Makefile，无 configure）
- 编译日期: 2026-05-28
- 编译器: clang/clang++ 15.0.4
- 状态: built

## 编译步骤

1. 源码获取：通过 git clone 从 GitHub 获取 v0.20.0 版本
2. 修改 Makefile：将 `ln -sf` 替换为 `rm -f && ln -s`（解决 HMDFS 不支持 ln -sf 覆盖的问题）
3. 构建：`make CC=clang CXX=clang++ PREFIX=$DEFAULT_PREFIX jsonnet jsonnetfmt libs`
4. 安装：`make PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX install`
5. 本地验证：`make PREFIX=$DEFAULT_PREFIX install`（不带 DESTDIR）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 版本不兼容 | CMakeLists.txt 使用 cmake_minimum_required(VERSION 2.8.7)，与 CMake 4.1.2 不兼容 | 改用 Makefile 构建（jsonnet 同时提供 Makefile 和 CMakeLists.txt） |
| 2 | HMDFS 不支持 ln -sf 覆盖 | Makefile 中使用 `ln -sf` 创建符号链接，HMDFS 文件系统限制 | 将 `ln -sf $< $@` 替换为 `rm -f $@ && ln -s $< $@`，生成补丁 0001-Makefile.patch |

## 源码修改

### Makefile (第 176-180 行)
修改符号链接创建方式，解决 HMDFS 兼容性问题：
```makefile
# 原代码
%.so.$(SOVERSION): %.so.$(VERSION)
	ln -sf $< $@

%.so: %.so.$(SOVERSION)
	ln -sf $< $@

# 修改后
%.so.$(SOVERSION): %.so.$(VERSION)
	rm -f $@ && ln -s $< $@

%.so: %.so.$(SOVERSION)
	rm -f $@ && ln -s $< $@
```

## 依赖版本

本次编译无外部库依赖，所有依赖（rapidyaml, md5）均为内置源码。

## 验证结果

```bash
$ ./jsonnet --version
Jsonnet commandline interpreter v0.20.0

$ ./jsonnetfmt --version
Jsonnet reformatter v0.20.0

# 测试结果
- snippet: PASS
- libjsonnet_test_snippet: PASS
- libjsonnet_test_file: PASS
- examples/check.sh: All 21 tests PASS
- examples/terraform/check.sh: All 4 tests PASS
- test_cmd: All 77 test scripts PASS
- test_suite: All 157 test scripts PASS
- run_fmt_tests: All 170 test scripts PASS
- run_fmt_idempotence_tests: PARTIAL (timeout terminated, 340 tests)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| jsonnet | 10M | Jsonnet 解释器 |
| jsonnetfmt | 10M | Jsonnet 格式化工具 |
| libjsonnet.so.0.20.0 | 10M | C 库 |
| libjsonnet++.so.0.20.0 | 10M | C++ 库 |

## 注意事项

1. jsonnet 同时提供 Makefile 和 CMakeLists.txt，但 CMakeLists.txt 版本要求过旧，建议使用 Makefile 构建
2. HMDFS 文件系统不支持 `ln -sf` 覆盖已存在的符号链接，需使用 `rm -f && ln -s` 替代
3. 测试套件较大（770+ 测试），执行时间较长，建议使用 timeout 控制执行时间
4. jsonnet 内置 rapidyaml 和 md5 库，无需外部依赖

## G0 验证特殊情况

**G0 干净构建验证部分通过**：
- ✅ 补丁应用成功（1/1）
- ❌ configure 步骤失败（jsonnet 无 configure 脚本）
- ✅ 实际构建成功（补丁自包含性验证完成）

**原因分析**：
- jsonnet 使用纯 Makefile 构建系统（`build_system: makefile`）
- G0 验证流程假设所有项目都有 configure 步骤
- 这是 skill 验证流程的局限，不是编译质量问题
**质量门禁**: G1-G4 PASS，G0 部分通过（纯 Makefile 项目特殊情况）
---

**编译结束**: 2026-07-15 22:49
**最终状态**: built
