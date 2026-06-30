# gpx

GPX 是一个 G-code 解析器/转换器，用于 3D 打印（MakerBot/RepRap）。
将切片软件生成的 G-code 文件转换为 X3G 格式，供 MakerBot 3D 打印机使用。

## 产物

| 二进制 | 说明 |
|--------|------|
| gpx | G-code 转 X3G 主程序 |
| s3gdump | s3g 格式转储工具 |
| machines | 机器配置文件生成工具 |

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 2.6.8 | published | 2026-06-29 |

## 构建系统

autotools (configure + make)

## 依赖

无外部依赖，仅依赖系统 libc。

## 源码

- 主页: https://github.com/markwal/GPX
- 许可证: GPL-2.0
