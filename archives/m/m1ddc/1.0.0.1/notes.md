# m1ddc 1.0.0.1 适配笔记

## 编译环境

- 构建系统: makefile（单文件 Objective-C CLI，Makefile 仅 `clang -fmodules -o m1ddc m1ddc.m`）
- 编译日期: 2026-08-28
- 编译器: clang（Conan profile `ohos-aarch64` 注入）
- 状态: 适配完成；版本目录与 Conan 包版本均为 `1.0.0.1`

## 上游信息

- 上游仓库: https://github.com/waydabber/m1ddc（官方正式源，MIT License）
- 版本策略: 任务给定版本为 `1`，但 Conan 2 不接受裸数字版本 `1`；源码复用上游 `v1.0.0` 官方归档。主线已有 `archives/m/m1ddc/1.0.0/` 且制品仓存在配方不同的 `m1ddc/1.0.0`，因此采用有效修复版本 `1.0.0.1`
- 源码归档: https://github.com/waydabber/m1ddc/archive/refs/tags/v1.0.0.tar.gz
- sha256: `884b65910e69915db29182363590d663a1a6d983e13ca5c41a74209058084c44`
- 归档内容: 仅 `LICENSE` / `Makefile` / `README.md` / `m1ddc.m` 四个文件

## 编译步骤

```bash
cd archives/m/m1ddc/1.0.0.1
conan create . -pr:h=../../../../ci/conan/profiles/ohos-aarch64 -pr:b=../../../../ci/conan/profiles/ohos-aarch64 --build=missing
```

配方实际构建命令与上游 Makefile 保持一致：

```bash
clang -fmodules -o m1ddc m1ddc.m
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游为 Apple Silicon 专用 macOS 工具 | `m1ddc.m` 使用 `@import Darwin/Foundation/IOKit` 与 Apple 私有 `IOAVService` 框架，OHOS clang 无 Darwin 模块，也无等价 Apple DDC 传输层 | `patches/0001-portable-nonapple.patch` 将源码拆为 `#ifdef __APPLE__` 原版实现与非 Apple 可移植 C 实现；可移植分支保留 CLI/帮助文本/VCP 码表/参数校验，真实 DDC 请求在无传输层时返回 no-display 失败 |
| 2 | 上游无任何测试套件 | 官方归档仅四个文件，无测试框架、测试目录或 `make check` 目标 | `test_package/MANIFEST.yml` 声明 `upstream_tests_exist: false` 并记录审计；`test_package/test.sh` 从消费者视角补充 6 个真实冒烟断言 |
| 3 | PR CI R40 分支名门禁失败 | `feat/m1ddc-1` 与有效 Conan 版本 `1.0.0.1` 不匹配；若强行把 Conan 版本改成 `1`，Conan 2 报 `Invalid package version '1'` | 使用有效 Conan 版本 `1.0.0.1`，任务分支调整为 `feat/m1ddc-1.0.0.1`，既无额外后缀也满足 R40 |
| 4 | AI 审查指出 display 错误路径返回 0 | 可移植分支中 `display <n> ...` 打印 display 不存在，却设置 `returnValue = 0` | 已改为非零退出；新增 test_package 断言覆盖 `m1ddc display 1 set volume 50` |
| 5 | AI 审查指出命令/VCP 参数校验不完整 | 初版非 Apple 分支只检查 VCP 参数，未先校验 `set/get/max/chg` 命令动词，VCP 错误提示也未覆盖完整表 | 新增 `command_supported()`，未知命令先报语法错误；未知 VCP 提示补齐 `input/standby/red/green/blue` 与别名说明 |

## 源码修改

- `patches/0001-portable-nonapple.patch`
  - 顶部插入 `#ifdef __APPLE__`，原上游 Apple 实现保持在该分支内
  - 追加非 Apple 可移植 C 分支，只依赖 `stdio/stdlib/string`
  - 保留 `display list`、`set/get/max/chg`、VCP 码表和帮助文本
  - 无 Apple `IOAVService` DDC 传输层时，对真实硬件请求返回确定性失败，不伪造成功
  - 修复审查意见：`display <n>` 错误路径非零退出，未知命令和未知 VCP 参数均有明确错误
- `conanfile.py`
  - `package_type = "application"`
  - `requirements()` 为空，无需拆分依赖库
  - `build()` 先调用 `apply_conandata_patches(self)`，再执行 `clang -fmodules -o m1ddc m1ddc.m`
  - `package()` 将 `m1ddc` 安装到 `bin/`
- `test_package/test.sh`
  - 使用 `set -euo pipefail`
  - 真实执行已安装的 `m1ddc` 二进制，覆盖 6 个断言
  - 输出 HMBS 测试标记，区分上游无测试与 test_package 新增测试

## B 类/路径 B 知识草稿

- 已补充 `knowledge/drafts/DRAFT-m1ddc-apple-ddc-transport-boundary.kv` 与 `knowledge/drafts/DRAFT-m1ddc-apple-ddc-transport-boundary.md`
- 候选知识点: Apple 私有硬件传输层缺失时，不删除 CLI、不伪造硬件 set/get 成功，而是保留可移植 CLI 合约并对真实设备请求诚实失败
- 提升边界: 草稿仅作为路径 B/B 类候选材料；未写入正式 `knowledge/graph/`、`knowledge/doc/` 或索引，最终是否认定由评审决定

## 验证命令

```sh
CI_PACKAGES="archives/m/m1ddc/1.0.0.1" zsh ci/conan/build_and_test.sh
```

```sh
/path/to/run-ohos-shadow-ci.sh archives/m/m1ddc/1.0.0.1
```

## 本机前置核验

- W0 依赖检查: `requirements()` 为空，`test_package` 只依赖 `self.tested_reference_str`
- 源码核验: 本地下载上游 `v1.0.0` 官方归档，sha256 与 `conandata.yml` 一致
- 构建系统核验: 上游 `Makefile` 仅执行 `clang -fmodules -o m1ddc m1ddc.m`，无测试目标
- 静态检查范围: 未发现 `${CC}`、`${CXX}`、`CFLAGS`、`LDFLAGS`、`LD_LIBRARY_PATH`、`PKG_CONFIG_PATH`、`/tmp`、`mktemp` 或 `settings.os == "Linux"` 硬编码
