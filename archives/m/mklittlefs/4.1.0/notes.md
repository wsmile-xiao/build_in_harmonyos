# mklittlefs 4.1.0 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-09-09
- 编译器: clang/clang++ (OHOS clang 15, aarch64)
- 状态: built

## 源码包说明

上游 4.1.0 官方发布物为 `mklittlefs-source.zip`，解压后顶层为 `src/`
目录，Makefile 位于 `src/Makefile`。zip 内已捆绑 littlefs 子模块
（tag v2.11.1, commit 8e251dd675da00342d45dac78b6f627f119aed03），
因此无需外部依赖，也无需构建期 git clone，满足离线确定性构建要求。

## 编译步骤

```bash
# conanfile.py 中等效命令（在 src/ 目录下执行）
make CC=clang CXX=clang++ \
     VERSION=4.1.0 LITTLEFS_VERSION=v2.11.1 \
     CXXFLAGS='-Wno-error=unused-command-line-argument' \
     CFLAGS='-Wno-error=unused-command-line-argument' \
     STRIP=true all
```

- `CC/CXX`: 上游 Makefile 硬编码 g++ 编译 main.cpp、默认 CC 编译
  littlefs 的 C 文件；OHOS PC 上仅有 clang 工具链，需显式注入。
- `VERSION/LITTLEFS_VERSION`: Makefile 默认 `git describe` 取版本，
  源码 zip 无 .git，必须显式固定，否则版本字符串不确定。
- `-Wno-error=unused-command-line-argument`: OHOS clang 封装自动注入
  `-Wl,--code-sign`，在 -Werror 下触发
  unused-command-line-argument 报错。
- `STRIP=true`: 上游默认对产物 strip；在 OHOS 上 strip 会去掉
  .codesign 段，导致二进制执行报 Operation not permitted。
  设 STRIP=true（no-op）保留签名段。

安装产物：`bin/mklittlefs`（单文件 CLI 工具）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|------|------|------|----------|
| 1 | 默认 make 报 -Werror=unused-command-line-argument | OHOS clang 注入 -Wl,--code-sign | CXXFLAGS/CFLAGS 追加 -Wno-error=unused-command-line-argument |
| 2 | strip 后二进制执行报 Operation not permitted | strip 去掉 .codesign 段 | STRIP=true 跳过 strip |
| 3 | Makefile 版本号来自 git describe | 源码 zip 无 .git | 显式传 VERSION=4.1.0 LITTLEFS_VERSION=v2.11.1 |
| 4 | 源码 zip 顶层为 src/，Makefile 不在根 | 上游发布物结构 | conanfile layout 设 folders.source/build = "src" |

## 源码修改

无补丁。所有平台差异通过环境变量注入，未修改上游源码。

## 依赖版本

无外部依赖。littlefs v2.11.1 与 tclap 头文件捆绑于官方源码 zip 内。

## 上游测试

`make test` → `run_tests.sh` → `tests/test_create`（bash 脚本，含 3 个
子测试），其 stdout 与 `tests/test_create.out` 精确比对。

本机（OHOS PC）实测：`tests/test_create` shebang 为 `#!/bin/bash`，
而 OHOS PC 无 /bin/bash，脚本无法直接执行（exit 126）。上游 CI
（GitHub Actions）也只构建不跑测试。详见下节。

## 验证结果

```bash
# conan create（任务 #8 执行）验证构建
# test_package 功能测试（任务 #5）：create/list/unpack 往返保真
# test_package/ohos 专测（任务 #6）：ELF64/AArch64、PT_INTERP、
#   .codesign、无宿主 RPATH、HMDFS 实跑 create/list/extract
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/mklittlefs | 镜像构建 CLI（ELF64 AArch64, OHOS 已签名） |
