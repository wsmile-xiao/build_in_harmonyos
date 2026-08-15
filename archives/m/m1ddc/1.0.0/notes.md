# m1ddc 1.0.0 适配笔记

## 编译环境
- 构建系统: makefile（单文件 Objective-C CLI，Makefile 仅 `clang -fmodules -o m1ddc m1ddc.m`）
- 编译日期: 2026-08-14
- 编译器: clang（/data/service/hnp/bin/clang，Conan profile ohos-aarch64 注入）
- 状态: 适配中（0001-portable-nonapple.patch 已接入，待 hmbs 真实机预检复跑）

## 上游信息
- 上游仓库: https://github.com/waydabber/m1ddc（官方正式源，MIT License）
- 源码归档: https://github.com/waydabber/m1ddc/archive/refs/tags/v1.0.0.tar.gz
- sha256: 884b65910e69915db29182363590d663a1a6d983e13ca5c41a74209058084c44（本地下载验证，归档内 m1ddc.m 与 GitHub raw v1.0.0 逐字节一致）
- 归档内容: 仅 LICENSE / Makefile / README.md / m1ddc.m 四个文件

## 编译步骤

```bash
# conan create（由 CI/预检执行，-pr 使用 ci/conan/profiles/ohos-aarch64）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 实际构建命令（配方 build() 内，与上游 Makefile 一致）
clang -fmodules -o m1ddc m1ddc.m
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游为 Apple Silicon 专用 macOS 工具 | m1ddc.m 使用 `@import Darwin/Foundation/IOKit` 与 Apple 私有 IOAVService 框架（I2C DDC 通道），OHOS clang 无 Darwin 模块（真机日志：`m1ddc.m:1:9: fatal error: module 'Darwin' not found`） | 新增 patches/0001-portable-nonapple.patch：把 m1ddc.m 拆为 `#ifdef __APPLE__`（原版原样保留）+ 可移植 C 实现（非 Apple 平台）。可移植实现保留完全相同的 CLI/帮助文本/VCP 码表/参数校验；无 Apple I2C 传输层时如实输出 "Could not find a suitable external display."，与上游无显示器时的行为一致。conanfile.py build() 补上缺失的 `apply_conandata_patches(self)` 调用 |
| 2 | 上游无任何测试套件 | 归档仅 4 个文件，无测试框架/目录/make check 目标（已审计确认） | test_package/MANIFEST.yml 声明 `upstream_tests_exist: false` + `upstream_test_audit`，输出 no_tests 标记（discovered:0 / executed:0） |
| 3 | 真机 /tmp 只读告警 | `/storage/Users/currentUser/preflight/clients/*/preflight.sh[229]: can't create temporary file /tmp/shooc0bi.tmp: Read-only file system` 来自 HMBS 自身 preflight.sh 包装脚本（ksh heredoc 临时文件），非配方代码（已 grep 确认配方/补丁/test_package 无 /tmp/mktemp/tempfile 硬编码），不致命 | 不为此改写配方（同 aribb24 先例） |

## 源码修改

- patches/0001-portable-nonapple.patch（patch_type: portability）
  - 顶部插入 `#ifdef __APPLE__` + 移植说明注释
  - 原 340 行上游代码（含 `@import` 与 IOAVService extern）保持原样在 `__APPLE__` 分支内
  - 文件末尾追加 `#else` 可移植 C 实现（`main` 完整复刻上游 CLI：display list/display N/set/get/max/chg 参数校验与输出文本；`vcp_code()` 与上游 VCP 码表一一对应）+ `#endif`
  - 可移植分支只依赖标准头（stdio/stdlib/string），无模块导入，`-fmodules` 在非 Apple 平台惰性
- conandata.yml: patches 列表注册 0001-portable-nonapple.patch
- conanfile.py: `from conan.tools.files import apply_conandata_patches`；build() 首行调用 `apply_conandata_patches(self)`（此前配方从未应用补丁——这是本次 `@import Darwin` 编译失败能被修复的前提）

## 补丁验证（本地，patch_ng 与真机 conan 同源）

```bash
# 以 conandata.yml 顺序（仅 1 个补丁）用 patch_ng 整体复验：
# ps.apply(root=..., strip=1) 返回 True，且应用后文件与预期新文件逐字节一致
# （经验 1 流程：本地用与真机一致的 patch_ng 复验补丁可应用性与结果正确性）
```

## 依赖版本

- 无编译依赖（requirements 为空），仅需 OHOS 自带 clang 15。

## 验证结果

```bash
# 待 hmbs 真实机预检（conan create + test_package）产出机器证据
# 预检日志中的 conan create 输出将作为 PR 正文「上游测试用例通过率」依据
```

## 注意事项

- 本库是 macOS/Apple Silicon 专属命令行工具，DDC/CI 硬件通道依赖 Apple 私有 IOAVService 框架；OHOS 无可移植等价 API，可移植实现如实报告无显示器（非伪造通过），真实机预检将验证编译与 test_package 3 个用例。
- 上游无测试用例（审计确认），PR 正文测试表由 HMBS 真机 evidence 生成，不手工填写数字。
