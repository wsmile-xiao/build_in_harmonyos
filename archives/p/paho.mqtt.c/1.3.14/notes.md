# paho.mqtt.c 1.3.14 — 适配笔记

> 编译日期: 2026-07-25
> 状态: published

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件 | paho.mqtt.c |
| 版本 | 1.3.14 |
| 构建系统 | CMake |
| 源码 | https://github.com/eclipse/paho.mqtt.c/archive/refs/tags/v1.3.14.tar.gz |

## 编译过程

### CMake 配置参数

```bash
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DPAHO_WITH_SSL=FALSE \
  -DPAHO_BUILD_STATIC=TRUE \
  -DPAHO_BUILD_SHARED=TRUE \
  -DPAHO_BUILD_DOCUMENTATION=FALSE \
  -DPAHO_BUILD_SAMPLES=FALSE
```

### 编译结果

✅ 全部 100% 编译成功，无错误无警告。

### 产物

| 文件 | 类型 |
|------|------|
| libpaho-mqtt3a.a / .so | 异步 MQTT 客户端库 |
| libpaho-mqtt3c.a / .so | 同步 MQTT 客户端库 |
| MQTTAsync.h / MQTTClient.h 等 7 个 | 头文件 |

## 平台适配

- 无需修改源码，原生兼容 HarmonyOS
- 无补丁需求
- 链接 pthread（标准 Linux/OHOS 行为）
- 未启用 SSL（系统缺少 OpenSSL 开发头文件）

## Conan 验证

G1-G4 + L2/L4/L5 全部 PASS，W3 本地 CI 模拟通过。
