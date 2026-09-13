# nfcutils — NFC 工具集（HarmonyOS PC 适配）

nfcutils 是 NFC（近场通信）工具集，本仓适配版本 **0.3.2**（nfc-tools/nfcutils 的
Google Code 时代发布版，2013-06）。该版本包含单个命令行工具：

- **lsnfc** — 列出 NFC 读卡器场内的 ISO14443A / ISO14443B / FeliCa 标签，
  并对 ISO14443A 标签做厂商/型号识别（MIFARE UltraLight / Classic / Plus /
  DESFire / JCOP 等，含 Ultralight C 与 DESFire EV1 深度识别）。

## 特性

- 纯 C、autotools 构建，依赖 **libnfc >= 1.7.0**（pkg-config 消费）
- 无 NFC 硬件时优雅报错（`ERROR: No device found.`，退出码 0）

## 构建

```bash
conan create archives/n/nfcutils/0.3.2 -pr:h ci/conan/profiles/ohos-aarch64 --build=missing
```

产物：`bin/lsnfc`（arm64 ELF）+ licenses/COPYING。

## 依赖

| 依赖 | 版本 | 说明 |
|---|---|---|
| libnfc | 1.8.0 | 静态库，pkg-config 消费；`libnfc.pc` Requires 为空，需显式追加 `-lusb -lusb-1.0` 链接 |

## 测试

上游无测试框架（归档仅 lsnfc.c 单源码 + Makefile，无 check/test 目标）。
test_package 提供消费者冒烟测试（3 断言）：

1. `bin/lsnfc` 存在且可执行
2. 无 NFC 硬件环境运行 lsnfc：输出含 `No device found`，退出码 0
   （上游真实行为：`nfc_list_devices()` 返回 0 → 优雅报错 → `EXIT_SUCCESS`），
   timeout 10s 防阻塞
3. 输出非空（工具真实执行）

## 已知限制

- 真实标签识别（MIFARE 深度识别、FeliCa 列表）依赖 NFC 读卡器硬件，
  无硬件环境下仅能验证优雅失败路径；硬件场景请在有 NFC 读卡器的设备上验证。
