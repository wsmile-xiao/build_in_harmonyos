# tinyframe

tinyframe 是 DNS-OARC 提供的轻量级 Frame Streams C 编解码库，用于生成和解析控制帧与数据帧。

## 版本

- 0.1.1

## 上游

- https://github.com/DNS-OARC/tinyframe

## HarmonyOS PC 适配

- 使用 Conan 2 与 Autotools 在 HarmonyOS PC aarch64 上构建。
- Git tag 源码通过 `autoreconf` 生成构建脚本。
- 保留并执行上游测试，同时提供独立消费者测试和 HarmonyOS 平台测试。
