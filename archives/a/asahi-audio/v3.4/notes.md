# asahi-audio v3.4 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-05-29
- 编译器: 无C/C++编译（纯数据包）
- 状态: built

## 编译步骤

asahi-audio 是 Apple Silicon Linux 音频DSP配置包，纯数据包无C/C++代码编译。

1. `source .build-context-asahi-audio-v3.4`
2. `cd $BUILD_SRC_DIR`
3. `make -j2 PREFIX=$DEFAULT_PREFIX` — 生成 aliases JSON 文件（sed处理graph.json/mic.json模板）
4. `make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX` — 安装79个文件

无 configure 步骤，无 make check 目标。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build下载超时 | GitHub网络不稳定 | 手动wget下载tarball到$TMPDIR/builds/，脚本检测到已存在直接使用 |
| 2 | init-build SSL证书更新超时 | HarmonyOS SSL验证问题 | 核心步骤已完成（orig/work目录、档案已建），手动生成build-context文件 |

## 源码修改

无源码修改，无需补丁。

## 依赖版本

- 无编译依赖（纯数据包）
- 运行时依赖: speakersafetyd, PipeWire >=1.0, WirePlumber >=0.5.2, Bankstown >=1.1.0, Triforce >=0.2.0, LSP Plugins >=1.0.20

## 验证结果

```bash
$ find $TEST_PREFIX -type f | wc -l
79
# 安装目录结构:
$TEST_PREFIX/$DEFAULT_PREFIX/share/asahi-audio/  — FIR数据（wav/json）按设备型号分目录
$TEST_PREFIX/$DEFAULT_PREFIX/share/wireplumber/  — WirePlumber配置和Lua脚本
$TEST_PREFIX/$DEFAULT_PREFIX/share/pipewire/     — PipeWire配置
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| packaging/asahi-audio-v3.4-aarch64.tar.gz | N/A | aarch64预编译包（纯数据包，无平台二进制） |
| packaging/asahi-audio-v3.4-aarch64-debug.tar.gz | N/A | aarch64-debug预编译包（纯数据包，无平台二进制） |

## 注意事项

- asahi-audio 是纯数据包，仅安装配置文件，不包含任何ELF二进制
- DESTDIR模式: PREFIX=$DEFAULT_PREFIX + DESTDIR=$TEST_PREFIX
- 此包专为Apple Silicon (Asahi Linux)设计，在OpenHarmony/aarch64上作为数据配置包使用
---

**编译结束**: 2026-07-15 21:49
**最终状态**: built
