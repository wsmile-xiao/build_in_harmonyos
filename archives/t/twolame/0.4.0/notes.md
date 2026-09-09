# twolame 0.4.0 适配笔记

## 编译环境
- 构建系统: autotools（configure + make，libtool）
- 编译日期: 2026-09-08
- 编译器: clang 15.0.4 / clang++
- 平台: HarmonyOS PC aarch64（HongMeng Kernel 1.12.0）
- 状态: built

## 编译步骤

```bash
# 官方 release tarball
# https://github.com/njh/twolame/releases/download/0.4.0/twolame-0.4.0.tar.gz
# sha256: cc35424f6019a88c6f52570b63e1baf50f62963a3eac52a03a800bb070d7c87d

./configure --prefix=$DEFAULT_PREFIX
make -j2
make install DESTDIR=$TEST_PREFIX
make check          # 上游测试，1/1 suite PASS（118 子用例）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: cannot guess build type | 内置 config.guess 2018-02-24 无 HarmonyOS 分支（uname -s=HarmonyOS 无法识别） | config.guess 增加 `*:HarmonyOS:*:*` 分支，输出 `aarch64-unknown-linux-ohos` 并 echo+exit（补丁 0001） |
| 2 | config.sub: Invalid configuration 'aarch64-unknown-linux-ohos' | config.sub 不认识 ohos 三元组 | 三处修补：maybe_os 列表加 linux-ohos\*、OS 列表加 -linux-ohos\*、-linux 归一化前特判 -linux-ohos 保持（补丁 0002） |
| 3 | config.status: can't create ./conf*/subs1.awk: Permission denied | config.status 以 `umask 077 && mktemp -d ./confXXXXXX` 建临时目录，HMDFS 上剥离组写权限 | configure 中 umask 077 → 002（补丁 0003），使临时目录保持组可写 |
| 4 | make check 找不到 frontend/twolame | twolame frontend 依赖 libsndfile，configure 检测不到时跳过 frontend 构建 | 从 ohpcd 制品仓拉取已发布 libsndfile/1.2.2（OHOS armv8 预编译），以 SNDFILE_CFLAGS/SNDFILE_LIBS 注入后 frontend 正常构建，make check 全过 |

## 源码修改

| 补丁 | 内容 |
|------|------|
| patches/0001-build-scripts-config.guess.patch | config.guess 识别 HarmonyOS，输出 aarch64-unknown-linux-ohos |
| patches/0002-build-scripts-config.sub.patch | config.sub 支持 ohos-linux 三元组（三处） |
| patches/0003-configure.patch | configure 临时目录 umask 077→002（HMDFS 组写兼容） |

> 补丁均平台移植类（platform_only），不含 __OHOS__ 平台宏。

## 依赖版本

- libsndfile 1.2.2（仅 frontend 构建与上游测试使用；库本身无强制依赖，conanfile.py requirements 为空）

## 验证结果

```bash
# 上游测试（make check）: 1/1 suite PASS
#   test.pl — 118 子用例（44100/22050/float32 WAV 编码，逐用例 MD5 指纹校验）
# HarmonyOS 消费者验证: test_package/test.c 真实调用 twolame API 完成 MP2 编码
#   twolame_init → set_num_channels(2) → set_in_samplerate(44100) → set_bitrate(192)
#   → init_params → encode_buffer(1024 samples) → encode_flush → close → exit 0
# Conan: conan-verify twolame 0.4.0 → G0/G1/G2/G3/G4/L2/L4/L5 全 PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | v3.0 Conan 配方（autotools，静态库 default，libs 仅 twolame） |
| conandata.yml | 官方 release 源 + sha256 + 3 个补丁声明 |
| test_package/ | CMake 消费者测试 + MANIFEST.yml（118 断言） |
| patches/ | 3 个平台移植补丁 |

## 注意事项

- 上游测试依赖 frontend（libsndfile），本地运行需注入已发布 libsndfile；CI 的 conan create 构建库本身无需该依赖（requirements 为空），上游测试已在本地实际运行并记录结果。
- 本归档不包含 .staging-verified 等运行时标记之外的额外产物；packaging/ 为 v3.0 说明文件。
---

**编译结束**: 2026-09-08 22:15
**最终状态**: published
