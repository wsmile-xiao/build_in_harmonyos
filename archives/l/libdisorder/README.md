# libdisorder

## 简介

libdisorder 是一个小型 C 库，用 Shannon 熵衡量字节流的随机性，并提供 `ropy` 命令行工具用于分析文件。

## HarmonyOS PC 适配

- 使用 Conan profile 中 `tools.build:compiler_executables` 指定的 OHOS Clang 构建静态库。
- 打包 `disorder.h`、`libdisorder.a` 和 `ropy`，不修改上游源码。
- 上游持续熵测试在 HarmonyOS 上原样运行，适配验证器收集并校验 3 轮后终止无限循环。
- 消费者测试覆盖库 API、`ropy` 工具以及 HarmonyOS 专有的 `__OHOS__`/AArch64 与 `/dev/urandom` 运行时路径。

## 依赖

- HarmonyOS C 运行库
- 系统数学库 `libm`

## 使用示例

```c
#include <disorder.h>

char data[] = {0, 1, 0, 1};
float entropy = shannon_H(data, sizeof(data));
```

```bash
ropy sample.bin
```

## 上游项目

- https://github.com/locasto/libdisorder

