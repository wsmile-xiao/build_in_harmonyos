# dmidecode

dmidecode 是一个读取计算机 SMBIOS（DMI）数据的工具，可以显示硬件信息如 BIOS、处理器、内存等。

## 功能概述
- 读取并解析 SMBIOS/DMI 数据
- 显示 BIOS、系统、主板、处理器、内存等硬件信息
- 支持多种输出格式
- 无外部依赖

## OHOS 适配
- 纯 Makefile 项目，直接 `make` 即可编译
- 无需任何补丁
- 注意：在非 x86/虚拟化环境中，DMI 数据可能不完整或不可用
- HarmonyOS 内核可能不完整暴露 SMBIOS 数据

## 依赖关系
- **编译依赖**: 无
- **运行依赖**: 无

## 参考资料
- 官网: https://www.nongnu.org/dmidecode/
- 源码: http://download.savannah.gnu.org/releases/dmidecode/
