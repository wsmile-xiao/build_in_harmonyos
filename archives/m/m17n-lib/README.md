# m17n-lib

## 简介

m17n-lib 是一个多语言文本处理库，为应用程序提供多语言输入、输出和显示功能。它是 m17n 项目的一部分，支持多种脚本和语言的文本处理。

## 功能概述

- 多语言输入方法支持
- 字符编码转换
- 文本布局和渲染
- 字体管理
- 输入法框架

## OHOS 适配要点

### 关键问题

HarmonyOS 的 `libintl.so.8.proxy` 使用符号重命名机制（如 `g_libintl_dgettext`），与标准 GNU libintl 的符号不兼容，会导致运行时符号查找失败。

### 解决方案

**静态链接 libintl.a**：
1. 使用 `--with-included-gettext` 编译内嵌的 libintl.a
2. 修改 `src/Makefile.am` 添加静态链接：
   ```makefile
   libm17n_core_la_LIBADD += $(top_builddir)/intl/libintl.a
   libm17n_core_la_DEPENDENCIES = $(top_builddir)/intl/libintl.a
   ```
3. 符号编译进共享库，运行时不再依赖系统 libintl.so

### 适用场景

此方案适用于所有在 HarmonyOS 上遇到 libintl 符号不兼容问题的软件，是通用的解决方案。

## 依赖关系

### 编译依赖
- libxml2（核心功能）

### 运行依赖
- libxml2
- 无需系统 libintl（已静态链接）

## 组件说明

- **libm17n-core**: 核心库（已静态链接 libintl.a）
- **libm17n**: 主库
- **libm17n-flt**: FLT 库
- **libm17n-gui**: GUI 库

## 参考资料

- 官网: https://www.nongnu.org/m17n/
- 源码: https://download.savannah.gnu.org/releases/m17n/
- 文档: https://www.nongnu.org/m17n/manual/