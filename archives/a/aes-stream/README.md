# aes-stream for HarmonyOS

## 概述

aes-stream 是 jedisct1（Frank Denis）开发的 AES-PRF 安全随机数生成器，
基于 AES-PRF（IACR ToSC 论文构造）与快速密钥擦除设计，可高效填充大缓冲区随机数据。
本归档为 HarmonyOS PC (aarch64) 平台的适配记录。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | aes-stream |
| 版本 | 20260924 |
| 上游仓库 | https://github.com/jedisct1/aes-stream |
| 授权 | BSD-2-Clause |
| 语言 | C |

## 适配说明

上游源码仅使用 x86 AES-NI intrinsics（immintrin.h / __m128i），无法在 OHOS arm64
目标编译。本归档携带 ARMv8 crypto extension（AESE/AESMC）移植实现
`20260924/src/aes-stream-arm.c`，逐位镜像上游构造，并已与标量参考实现
bit-exact 对拍（AES-128/AES-256，多种子多长度）。移植方案、FIPS-197 KAT
与对拍验证详情见 `20260924/notes.md` 与 `20260924/reports/test-report.md`。

## 验证

- conan-verify：G0-G4 + L2/L4/L5 全部通过
- W3 本地 CI 模拟：conan create + test_package 通过
- 上游测试：官方源码无任何测试入口（台账见 20260924/notes.md）
- 鸿蒙专项：test_package KAT/确定性/非全零/key-erasure 断言全部通过
