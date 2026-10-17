# libwapcaplet 0.4.3 适配笔记

## 编译环境

- 构建系统: makefile（NetSurf Makefile → standalone Makefile 替换）
- 编译日期: 2026-09-14（首轮工作树，待 HMBS 真机预检）
- 编译器: clang/clang++ (15, /data/service/hnp/bin)
- 归档工具: llvm-ar / llvm-ranlib
- 状态: built（首轮工作树状态，证据轮按真机实测校准）

## 与历史版本的关系

- 本目录为上游原生版本 0.4.3 的首次适配（R37：首次适配用上游版本，无后缀）。
- 0.4.3.1/0.4.3.2 为同一上游源码行的历史适配分支：0.4.3.1 验证 standalone
  Makefile 路线可行；0.4.3.2 沉淀了 E120（lld 缺 libxml2.so.16）、R33
 （dict conf 取编译器）、L0d（test() 字面 self.run）三项修复。
- 本配方以 0.4.3.2 为基线，并做三处改进：
  1. 源码回官方 netsurf tarball（0.4.3-src.tar.gz，sha256 与 0.4.3.1 实测一致），
     不再用 github archive（R39 官方源优先；netsurf 域无 CI 镜像映射，
     若真机/CI 下载超时再按守则改写为有序 URL 列表）；
  2. 补丁 PREFIX 默认值改为通用 `/usr/local`（历史补丁硬编码了某 worker 的
     `/storage/...` 本地路径，conan 传入 PREFIX 时无影响，但默认值不应泄漏
     环境特异路径；COMPONENT_VERSION 保持 0.4.3 不变）；
  3. 按 HMBS 机器证据硬门禁补齐标记：build() 运行上游等价检查并输出
     `HMBS_UPSTREAM_TEST_RESULT`（结果持久化到包内 `res/hmbs_upstream.json`），
     test_package 输出 `HMBS_TEST_PACKAGE_RESULT` 并在缓存命中时复发上游证据
    （沿用 ayatana-ido/0.10.4-v2 既定模式）。

## 编译步骤

1. 下载官方源码包 `libwapcaplet-0.4.3-src.tar.gz` 并解压
2. 补丁 0001-Makefile.patch 将顶层 Makefile 替换为 standalone Makefile
   （CC/AR/RANLIB 变量化、去 -Werror 兼容 clang 15、PREFIX/DESTDIR 安装规则）
3. 编译: `make CC=<conf c> AR=<conf ar> RANLIB=<conf ranlib> -j1`
4. 上游等价检查：编译运行内嵌 `upstream_check.c`（12 项 CHECK_PASS）
5. 安装: `make install PREFIX=<package_folder>`
6. test_package：CMake 消费者测试，真实调用 lwc_string_* API（16 个断言）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | NetSurf 构建系统依赖 (`NSSHARED`) | 原始 Makefile include `$(NSSHARED)/makefiles/Makefile.tools`，netsurf-buildsystem 包不可用 | 补丁替换为 standalone Makefile（沿用 0.4.3.1/0.4.3.2 结论） |
| 2 | lld 链接器缺 libxml2.so.16 | OHOS SDK 的 lld 运行时依赖 libxml2，worker 默认 loader 路径找不到 | recipe 与 test_package 的 build() 注入 SDK llvm lib 目录到 `LD_LIBRARY_PATH`（E120） |
| 3 | 上游 `make check` 依赖 libcheck | test/testmain.c 直接 `#include <check.h>`，本平台无 libcheck 包 | build() 运行等价检查覆盖同一组 API（12 项）；test_package 消费者复验（16 断言）；审计见 test_package/MANIFEST.yml |
| 4 | R33 dict conf 误用 | `tools.build:compiler_executables` 是 dict，不能用子键语法 `:c` 读取 | 整体读取 dict 后取 `c`/`ar`/`ranlib` 键（沿用 0.4.3.2 修复） |
| 5 | CI L0d stub_test_method 风险 | test() 仅 `cmake.test()` 无字面 `self.run` 会被判空壳 | test() 保留 `self.run(bash -c '<binary>', env="conanrun")` 真实执行（沿用 0.4.3.2 修复） |

## 源码修改

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|----------|
| Makefile | NetSurf 构建系统不可用 | 完全替换为独立 Makefile | patches/0001-Makefile.patch（已固化） |

## 依赖版本

- 无运行时依赖
- 编译工具: clang 15, llvm-ar, llvm-ranlib, GNU make, cmake（test_package）

## 验证结果

- 首轮为工作树准备轮：本机（Windows）不运行 conan，待 HMBS 后台真机预检。
- 预期证据（待预检日志回填）：
  - `HMBS_UPSTREAM_TEST_RESULT`：discovered=12/executed=12/passed=12
  - `HMBS_TEST_PACKAGE_RESULT`：discovered=16/passedCount=16
  - ctest：1/1 passed（test_libwapcaplet）
- 证伪要求（预检通过前核对）：检查 `upstream_check` 与 `test_libwapcaplet`
  输出非空且含逐项 PASS 行；抽查把被测调用改错时 harness 是否报失败；
  确认 0 跳过（跳过计入 skipped 即判不通过）。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（makefile 模板，静态库，package_info.libs=[wapcaplet]，含上游等价检查与证据标记） |
| conandata.yml | 官方 URL + sha256 + 补丁声明 |
| test_package/ | CMake 消费者测试（test.c 16 断言，真实调用 API，含证据标记与复发逻辑） |
| patches/0001-Makefile.patch | standalone Makefile 替换补丁（通用 PREFIX 默认值） |
| libwapcaplet.a | 静态库（待预检产出） |
| libwapcaplet.pc | pkg-config 文件（待预检产出） |
| libwapcaplet/libwapcaplet.h | 头文件（待预检产出） |

## 注意事项

- libwapcaplet 是 NetSurf 浏览器组件库，使用 NetSurf 自有的构建系统而非标准 autotools
- 此平台需替换为独立 Makefile 进行编译
- 静态库无需 ELF 签名 / RPATH（.a 不可直接执行）
- `-j1` 约束（HMDFS 上 make jobserver mkfifo 报 EPERM，E074）
- 本轮严禁 commit/push/建 PR；证据轮通过后由 HMBS 统一提交并建 PR
---

**编译结束**: 待 HMBS 真机预检
**最终状态**: built（首轮工作树，待证据校准）
