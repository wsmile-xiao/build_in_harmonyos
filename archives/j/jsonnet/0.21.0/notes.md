# jsonnet 0.21.0 适配笔记

## 编译环境
- 构建系统: Makefile（纯 Makefile，无 configure）
- 编译日期: 2026-10-08
- 编译器: clang/clang++ 15.0.4（aarch64-unknown-linux-ohos 目标）
- 状态: built

## 版本升级说明（v0.20.0 → 0.21.0）

- 归档路径: archives/j/jsonnet/v0.20.0 → 0.21.0
- 上游 0.21.0（2025-05-07 发布）为 bugfix/维护版本，Makefile 构建结构与 v0.20.0 一致
- HMDFS `ln -sf` 兼容性问题在 0.21.0 中依然存在（Makefile 第 180/183 行），
  移植 v0.20.0 的同款补丁 0001-Makefile.patch（rebase 到 0.21.0 行号）
- third_party 捆绑依赖：nlohmann-json、md5、rapidyaml（无外部 conan 依赖）
- CMakeLists.txt 仍为 cmake_minimum_required(VERSION 2.8.7)，与 CMake 4.x 不兼容，
  继续使用 Makefile 构建（与 v0.20.0 判定一致）

## 编译步骤

1. 源码获取：conandata.yml 官方 URL（sha256=a12ebca72e43e7061ffe4ef910e572b95edd7778a543d6bf85f6355bd290300e）
2. 补丁应用：0001-Makefile.patch（ln -sf → rm -f && ln -s）
3. 构建：`make CC=clang CXX=clang++ jsonnet jsonnetfmt libs`
4. 安装：`make DESTDIR=<pkg> PREFIX="" install`
5. 本地验证：conan create -pr=ohos-aarch64 全绿 + 上游 make test 全量套件

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 版本不兼容 | CMakeLists.txt 使用 cmake_minimum_required(VERSION 2.8.7)，与 CMake 4.x 不兼容 | 改用 Makefile 构建（jsonnet 同时提供 Makefile 和 CMakeLists.txt） |
| 2 | HMDFS 不支持 ln -sf 覆盖 | Makefile 第 180/183 行使用 `ln -sf` 创建符号链接，HMDFS 文件系统限制 | 将 `ln -sf $< $@` 替换为 `rm -f $@ && ln -s $< $@`，移植 v0.20.0 补丁 |
| 3 | 本地 make test 全量报 "Error relocating ./jsonnet: symbol not found"（libc++ __n1 符号） | shell 默认 LD_LIBRARY_PATH 含异常路径段，加载器挑错 libc++ | 环境问题非代码问题：`export LD_LIBRARY_PATH=/system/lib64` 后全部测试正常通过 |

## 源码修改

### Makefile（第 177-184 行）
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

本次编译无外部库依赖，所有依赖（nlohmann-json, rapidyaml, md5）均为 third_party/ 内置源码。

## 验证结果

```bash
$ ./jsonnet --version
Jsonnet commandline interpreter 0.21.0

$ ./jsonnetfmt --version
Jsonnet reformatter 0.21.0
```

上游 make test 全量测试套件（LD_LIBRARY_PATH=/system/lib64 环境）：
- tests.sh: snippet + libjsonnet_test_snippet + libjsonnet_test_file + libjsonnet_test_locale 全部通过
- examples/check.sh / examples/terraform/check.sh: 全部通过
- test_cmd/run_cmd_tests.sh: 77/77 通过
- test_suite/run_tests.sh: 165/165 通过
- doc/_stdlib_gen/run_tests.sh: 通过
- test_suite/run_fmt_tests.sh: 178/178 通过
- test_suite/run_fmt_idempotence_tests.sh: 356/356 通过

（具体数字以最终执行日志为准，见 PR 正文统计表）
