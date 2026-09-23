# m1ddc 1.2.0 适配笔记

## 编译环境

- 构建系统：makefile（多文件 Objective-C CLI：sources/i2c.m、sources/ioregistry.m、sources/m1ddc.m，Makefile 执行 `clang -fmodules -I headers` 编译并链接 `-framework CoreDisplay`）
- 编译日期：2026-09-09
- 编译器：clang（Conan profile `ohos-aarch64` 注入）
- 状态：适配完成待真机预检；版本目录与 Conan 包版本均为 `1.2.0`

## 上游信息

- 上游仓库：https://github.com/waydabber/m1ddc（官方正式源，MIT License）
- 版本策略：首次适配上游 `1.2.0`，目录与包版本直接使用 `1.2.0`
- 源码归档：https://github.com/waydabber/m1ddc/archive/refs/tags/v1.2.0.tar.gz
- sha256：`d633c06502e650108bb2f581b5db25d2592955fa9a57de7feeae3ed7710c59ca`（本地下载 10417 字节验证）
- 归档内容：`LICENSE`、`Makefile`、`README.md`、`headers/i2c.h`、`headers/ioregistry.h`、`headers/utils.h`、`sources/i2c.m`、`sources/ioregistry.m`、`sources/m1ddc.m`，共 9 个文件
- 与 1.0.0 差异：1.0.0 为单文件 `m1ddc.m`，1.2.0 拆分为 I2C 数据包、IO 注册表枚举和主命令三模块，并新增类库目标（`libm1ddc.a` 与合并头），扩展 `input-alt`、`pbp`、`pbp-input` 控制和 `display list detailed` 及多种显示器标识方法

## 编译步骤

```bash
cd archives/m/m1ddc/1.2.0
conan create . -pr:h=../../../../ci/conan/profiles/ohos-aarch64 -pr:b=../../../../ci/conan/profiles/ohos-aarch64 --build=missing
```

配方实际构建命令与上游 Makefile 保持一致，仅去掉 OHOS 不存在的 Apple 链接标志：

```bash
clang -fmodules -I headers -o m1ddc sources/i2c.m sources/ioregistry.m sources/m1ddc.m
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游为 Apple Silicon 专用 macOS 工具 | 三个源文件使用 `@import Darwin/Foundation/IOKit/CoreGraphics/ApplicationServices` 与 Apple 私有 `IOAVService` 框架，OHOS clang 无 Darwin 模块，也无等价 Apple DDC 传输层 | `patches/0001-portable-nonapple.patch` 将三个源文件拆为 `__APPLE__` 原版分支与非 Apple 分支：i2c 与 ioregistry 在非 Apple 平台编译为空桩，m1ddc.m 在非 Apple 平台提供可移植 C 实现，保留 CLI、帮助文本和 VCP 码表，真实 DDC 请求在无传输层时返回无显示器失败 |
| 2 | 上游无任何测试套件 | v1.2.0 归档仅 9 个源码与文档文件，无测试框架、测试目录或 `check`、`test` 目标 | `test_package/MANIFEST.yml` 声明 `upstream_tests_exist: false` 并记录审计；`test_package/test.sh` 从消费者视角补充 6 个真实冒烟断言 |
| 3 | 多文件结构导致旧单文件补丁无法复用 | 1.0.0 系列补丁只处理根目录 `m1ddc.m`，1.2.0 源码移至 `sources/` 并新增两模块与公共头 | 为 1.2.0 重新生成三文件补丁，公共头无需改动（仅在 `__APPLE__` 分支内引用），配方编译三个源文件并保留 `-fmodules` 与 `-I headers` |
| 4 | 无参数与帮助退出码与旧版本不同 | 1.2.0 上游 `argc < 2` 时打印用法并返回 `help` 参数为 1、无参数为 0，旧版 test 断言无参数返回非零 | 可移植分支逐字复刻该语义，test_package 第 1 个用例改为验证无参数输出用法且退出码为 0 |

## 源码修改

- `patches/0001-portable-nonapple.patch`
  - 三个源文件顶部插入 `__APPLE__` 守卫与移植说明注释，原上游 Apple 实现保持在该分支内
  - `sources/i2c.m` 与 `sources/ioregistry.m` 在非 Apple 分支仅保留空桩类型，避免空翻译单元告警
  - `sources/m1ddc.m` 在非 Apple 分支追加可移植 C 实现，只依赖 `stdio/stdlib/string`
  - 复刻 1.2.0 的帮助文本、命令动词（`set/get/max/chg`）、VCP 码表（含 `input-alt`、`pbp`、`pbp-input` 与单字母别名）、`display list` 与显示器选择、`-v/--verbose` 透传、`Missing value` 与 `Invalid command` 校验
  - 无 Apple `IOAVService` DDC 传输层时，对真实硬件请求返回确定性失败，不伪造成功
- `conanfile.py`
  - `package_type = "application"`
  - `requirements()` 为空，无需拆分依赖库
  - `build()` 先调用 `apply_conandata_patches(self)`，再执行三文件 `clang -fmodules -I headers` 编译
  - `package()` 将 `m1ddc` 安装到 `bin/`
- `test_package/test.sh`
  - 使用 `set -euo pipefail`
  - 真实执行已安装的 `m1ddc` 二进制，覆盖 6 个断言
  - 输出 HMBS 测试标记，区分上游无测试与 test_package 新增测试

## B 类/路径 B 知识草稿

- 沿用 `knowledge/drafts/DRAFT-m1ddc-apple-ddc-transport-boundary.kv` 与配套文档
- 候选知识点：Apple 私有硬件传输层缺失时，不删除 CLI、不伪造硬件 set/get 成功，而是保留可移植 CLI 合约并对真实设备请求诚实失败
- 本次 1.2.0 将该模式从单文件扩展到多文件模块（传输层模块空桩化，主命令模块可移植化），未写入正式 `knowledge/graph/`、`knowledge/doc/` 或索引，最终是否认定由评审决定

## 验证命令

```sh
CI_PACKAGES="archives/m/m1ddc/1.2.0" zsh ci/conan/build_and_test.sh
```

## 本机前置核验

- W0 依赖检查：`requirements()` 为空，`test_package` 只依赖 `self.tested_reference_str`
- 源码核验：本地下载上游 `v1.2.0` 官方归档，大小 10417 字节，sha256 与 `conandata.yml` 一致
- 构建系统核验：上游 `Makefile` 默认目标为 `binary`，编译三个 `sources/*.m` 并链接 `-framework CoreDisplay`，无 `check` 或 `test` 目标
- 静态检查范围：配方、补丁和 test_package 无 `${CC}`、`${CXX}`、`CFLAGS`、`LDFLAGS`、`LD_LIBRARY_PATH`、`PKG_CONFIG_PATH`、`/tmp`、`mktemp` 或 `settings.os == "Linux"` 硬编码；补丁平台宏仅使用 `__APPLE__`，未引入 `__OHOS__`
