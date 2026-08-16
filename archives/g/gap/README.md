# gap

**GAP — 计算离散代数系统（群论为主）— gap 交互/批处理可执行文件 + libgap 共享库 + GAP 包树**

## 命令行工具

- `gap`

## 库

- `libgap.so`

## 构建

- 构建系统：autotools
- 许可证：GPL-2.0-or-later
- 上游：https://www.gap-system.org/

## 依赖

- `gmp/6.3.0`
- `zlib/1.3.1.1`

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 4.16.0 | built | 首个鸿蒙 PC conan 配方 |

## 为什么做这个包

passagemath（SageMath 的模块化重打包）在鸿蒙 PC 上的 wheel 需要它作为原生底座。
