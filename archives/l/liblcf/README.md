# liblcf

## 简介
liblcf 是 EasyRPG 项目的一部分，用于读取和写入 RPG Maker 2000/2003 的 LCF 格式文件（游戏数据库和地图数据）。

## 版本
- 当前版本: 0.8.1

## 依赖
- 无外部依赖（基础功能模式）
- 可选依赖: ICU, Expat, inih（未启用）

## 特性
- 支持 LDB, LMT, LMU, LSD 等格式
- 提供 C++ API
- 支持 Windows-1252 编码（基础模式）

## 编译说明
- 构建系统: CMake
- 平台适配: HMDFS 不支持 autotools 临时目录，改用 CMake
- 功能限制: 禁用了 ICU/XML/INI 支持

## 归档位置
`archives/l/liblcf/0.8.1/`