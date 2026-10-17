# cdem

Connected Digital Energy Meter (CDEM) 是一个用于解析比利时数字电表 DSMR 报文的便携 C 库。上游为面向 ESP8266 的 Arduino 库，本仓库将其适配为 HarmonyOS PC 可用的 header-only 形态，剥离 Arduino 依赖，提供纯 C 的版本与报文解析辅助接口。

## OHOS 适配

- **上游来源**: https://github.com/connected-digital-energy-meter/connected-digital-energy-meter `v1.0` (version 1.0.0)
- **构建系统**: CMake INTERFACE library，header-only，无需编译
- **适配要点**: 在 `source()` 阶段生成 `include/cdem/cdem.h` 与配套 `cdem.c` 实现，提供 `cdem_create`/`cdem_destroy`、`cdem_version_*`、`cdem_parse_telegram` 等 portable API；上游的 Arduino 相关头文件（ArduinoJson、PubSubClient 等）不参与 OHOS 构建
- **许可证**: MIT（上游）

## 依赖

- 无外部依赖，仅需 C 标准库与 C++ 编译器（OHOS clang 15）

## 功能验证

```bash
pkg-config --modversion cdem  # 无 pkg-config，改用 cmake 查找
# 或直接编译 test_package
```

## 参考

- 官网: https://connected-digital-energy-meter.netlify.app
- 源码: https://github.com/connected-digital-energy-meter/connected-digital-energy-meter
