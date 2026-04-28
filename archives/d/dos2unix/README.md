# dos2unix

dos2unix/unix2dos 是 DOS/MAC 与 Unix 文本格式转换工具，版本 7.5.4，支持 Unicode UTF-16。

## 功能概述
- CRLF ↔ LF 转换（DOS ↔ Unix）
- CR ↔ LF 转换（Classic Mac ↔ Unix）
- Unicode UTF-16/UTF-8 转换
- 支持标准输入/输出管道操作
- 二进制文件自动跳过
- 支持文件编码检测和转换

## OHOS 适配
- 纯 Makefile 项目，无 configure 脚本
- **必须禁用 NLS**：HarmonyOS 缺少 libintl/gettext
- **注意**：`ENABLE_NLS = 0` 也会被 `ifdef` 视为 true（"0" 非空），必须设为空值 `ENABLE_NLS =`
- **软链接问题**：HarmonyOS SELinux 限制 `ln -sf` 在部分目录的使用，需改为 `ln -s` 或 `cp`
- 核心功能（dos2unix/unix2dos）完全可用（83/115 测试通过）
- mac2unix/unix2mac 相关测试因软链接限制失败，不影响实际功能

## 依赖关系
- **编译依赖**: 无（NLS 已禁用）
- **运行依赖**: 无

## 参考资料
- 官网: https://waterlan.home.xs4all.nl/dos2unix.html
- 源码: https://sourceforge.net/projects/dos2unix/
