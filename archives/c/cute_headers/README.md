# cute_headers

cute_headers 是一组自包含的单文件 C/C++ 跨平台库头文件集合。

## 功能概述

- `cute_c2`：二维碰撞检测与射线查询
- `cute_png`：PNG 加载与保存
- `cute_tiled`：Tiled 地图 JSON 加载
- `cute_sound`、`cute_net`、`cute_sync`、`cute_tls` 等实用组件

## OHOS 适配

该项目为 header-only 库，无需生成动态或静态库。配方将全部 `cute_*.h` 安装到 Conan 的 `include/` 目录。在 OHOS arm64 上已通过 `cute_c2` 实际 API 消费者测试。使用某个组件的实现时，需在一个翻译单元中定义对应的 `CUTE_*_IMPLEMENTATION` 宏。

## 依赖关系

无外部编译或运行时依赖。

## 参考资料

- https://github.com/RandyGaul/cute_headers
