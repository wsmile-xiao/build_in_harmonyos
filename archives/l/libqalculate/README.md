# libqalculate

libqalculate 是一个用于精确计算、单位转换等功能的数学计算库。

## 基本信息

- **主页**: https://qalculate.github.io/
- **许可证**: GPL-2.0
- **分类**: math

## OpenHarmony 适配要点

1. **构建系统**: 仅支持 autotools，不支持 CMake
2. **shebang**: 需修改为 `/usr/bin/env/bash`（toybox sh 不兼容）
3. **XML::Parser**: XS 模块因 HMDFS dlopen 限制无法加载，使用 `cp` 替代 intltool-merge
4. **umask**: 改为 022 解决临时目录权限问题
5. **pthread_cancel**: OpenHarmony 不支持，需条件编译跳过

## 依赖

- gmp
- mpfr
- libxml2

## 已编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 5.4.0 | published | 2026-05-26 |