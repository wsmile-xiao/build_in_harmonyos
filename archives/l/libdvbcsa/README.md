# libdvbcsa

libdvbcsa 是一个免费的 DVB CSA（Common Scrambling Algorithm）加密/解密库实现，用于数字视频广播（DVB）系统的内容加扰与解扰。

## 功能特性

- **单包模式 (Single Packet)**: 提供 `dvbcsa_encrypt/dvbcsa_decrypt` API，逐包处理 CSA 加解密
- **并行比特切片模式 (Bitslice)**: 提供 `dvbcsa_bs_encrypt/dvbcsa_bs_decrypt` API，批量并行处理多个数据包，性能更高
- 支持标准 8 字节 CSA 控制字 (CW)
- 同时生成动态库 (.so) 和静态库 (.a)

## 鸿蒙平台适配

- **版本**: 1.1.0
- **构建系统**: autotools
- **编译器**: clang/clang++
- **补丁**: 3 个平台适配补丁 (config.guess, config.sub, configure)
- **运行时依赖**: 仅 libc.so（系统库）
- **状态**: built (功能测试 24/24 PASS)

## 使用方式

```bash
# 安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libdvbcsa 1.1.0

# 编译链接
aarch64-unknown-linux-ohos-clang -o myapp myapp.c -ldvbcsa
```

## 注意事项

- 上游不提供 pkg-config (.pc) 文件，依赖软件需通过 `-ldvbcsa` 直接链接
- 标准 MPEG-TS payload 长度为 184 字节

## 许可证

GPL-2.0-or-later