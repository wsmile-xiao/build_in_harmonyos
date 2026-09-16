# vo-amrwbenc 0.1.3 for HarmonyOS

## 概述

VisualOn AMR-WB 编码器库在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南和测试记录。

## 构建与验证

- 构建系统: autotools（SourceForge 发布 tarball，自带 configure）
- 适配要点: umask 077 放宽（E011 同源）、config.sub triplet 兼容（vo-aacenc 先例）
- 消费者测试: 经 CMake 链接 libvo-amrwbenc，调用 E_IF_init/E_IF_encode/E_IF_exit 编码两帧并断言 61 字节 RFC 3267 帧

详见 notes.md 与 manifest.yaml。
