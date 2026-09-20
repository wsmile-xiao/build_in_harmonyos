# libopusenc 0.3 HarmonyOS PC 适配笔记

## 编译环境

- 构建系统: autotools
- 编译日期: 2026-09-17
- 编译器: clang/clang++（ohos-aarch64，aarch64-unknown-linux-ohos）
- 状态: built

## 源码信息

- 官方源码: `https://downloads.xiph.org/releases/opus/libopusenc-0.3.tar.gz`（408391 字节）
- SHA256: `f616d3aff9b2034547894ccb8ab56c36cf1a4acb0d922c5d7119f97bbe58642c`
- 许可证: BSD-3-Clause（COPYING: Xiph.Org Foundation and contributors）

## 依赖版本

上游 configure.ac 仅声明 `PKG_CHECK_MODULES([DEPS], [opus >= 1.1])`。
libopusenc 自带 `src/ogg_packer.c` 打包 Ogg 页，**不依赖 libogg**。

- opus/1.5.2.1（制品仓已发布，满足 opus >= 1.1）

## 编译步骤

Conan 2 + AutotoolsDeps/AutotoolsToolchain + PkgConfigDeps：

1. 解压官方 tarball，`apply_conandata_patches()` 应用 0001/0002 补丁；
2. `configure --host=aarch64-unknown-linux-ohos`（ Conan AutotoolsToolchain 生成）；
3. `make -j`；
4. staging 收集构建产物（`libopusenc.so`/`libopusenc.a`、`include/opus/opusenc.h`、`libopusenc.pc`、`COPYING`）打包。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 2024-07-27 版脚本无 HarmonyOS 分支 | 0001 补丁加 `*:HarmonyOS:*:*` 分支，`LIBC=ohos` |
| 2 | configure 阶段 config.status 临时目录创建失败 | HMDFS 上 umask 077 产生的目录权限问题 | 0002 补丁将临时目录 umask 放宽为 022 |
| 3 | config.sub 是否需要补丁 | 2024 版 config.sub 已原生接受 linux-ohos | 无需补丁（与 0.2.1 不同，0.3 已原生支持） |

## 源码修改

- `patches/0001-config-guess-ohos.patch`: config.guess 增加 HarmonyOS 识别（E007 复用）
- `patches/0002-configure-hmdfs-temp-mode.patch`: configure 临时目录权限修复（E011 复用）

## 上游测试清点

`Makefile.am` 无 `TESTS`、`check_PROGRAMS`、`check-local` 条目——上游正式测试数为 **0**。
`examples/opusenc_example.c` 是 noinst 示例，不计入上游正式测试。

## 知识复用

路径 A（纯复用，无新增知识条目）：

- E007: config.guess/config.sub GNU 三元组识别
- E011/E122: Autoconf 临时目录权限（HMDFS）
- E072: Autotools 构建执行器路径

## 验证结果

```bash
readelf -d libopusenc.so
NEEDED: libopus.so.0, libc.so
SONAME: libopusenc.so
readelf -h libopusenc.so
Class: ELF64, Machine: AArch64
```

test_package 用真实 API（ope_encoder_create_file / ope_encoder_write / ope_encoder_drain）
编码确定性 PCM 到 Ogg Opus 文件，逐页校验 OggS 魔数、OpusHead/OpusTags 头与 EOS 标志。

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libopusenc.a 或 lib/libopusenc.so | static / shared 双产物（shared 用 `-avoid-version` 生成无版本后缀真实文件） |
| include/opus/opusenc.h | 公共 API 头 |
| lib/pkgconfig/libopusenc.pc | pkg-config 元数据 |
| licenses/COPYING | 许可证文件 |
