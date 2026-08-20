# nim 2.2.8 — OpenHarmony 编译记录

## 基本信息
- 软件: nim
- 版本: 2.2.8
- 构建系统: custom (Nim self-hosted bootstrap)
- 目标: ohos-aarch64
- 主页: https://nim-lang.org
- 许可证: MIT

## 编译指导
Nim 编译器本身用 Nim 编写，需要通过 csources_v3 (纯 C) bootstrap 编译。
关键参数: `uos=linux` (HarmonyOS uname 不匹配 Makefile)、`--cc:clang` (指定 C 编译器)。
csources_v3 从 https://github.com/nim-lang/csources_v3.git 克隆。

## 补丁清单
无补丁。所有适配通过编译参数解决。

## 已知限制
- csources_v3 需要网络访问（git clone）
- OHOS SDK 的 lld 需要 LD_LIBRARY_PATH 包含 SDK lib 目录

## 功能验证
```bash
nim --version
# Nim Compiler Version 2.2.8 [Linux: arm64]
```
