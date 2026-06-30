# astroterm 1.0.9-r0 编译笔记

## 编译环境
- Meson 1.4.0
- Ninja 1.13.1
- Clang 15.0.4
- OHOS SDK 26.0.0.18

## 编译步骤

### 1. 依赖准备
- argtable3 3.3.1: 从源码编译静态库
  - URL: https://github.com/argtable/argtable3/archive/refs/tags/v3.3.1.tar.gz
  - 编译: 直接使用 clang 编译源码文件生成静态库
  
- bsc5 数据文件: 从 Yale Harvard 下载
  - URL: http://tdc-www.harvard.edu/catalogs/BSC5
  - SHA256: e471d02eaf4eecb61c12f879a1cb6432ba9d7b68a9a8c5654a1eb42a0c8cc340

### 2. 源码修改
- parse_BSC5.h: 在 <string.h> 前添加 #include <stddef.h>
- embed.sh: 替换 xxd 命令为 Python 脚本

### 3. 构建命令
```bash
meson setup build --prefix=$DEFAULT_PREFIX
cd build
ninja astroterm
ninja install
```

## 问题与方案

### 问题1: OHOS SDK fortify/string.h size_t 重定义
**原因**: OHOS SDK 的 fortify/string.h 头文件需要 size_t 类型已定义
**方案**: 在 <string.h> 之前添加 #include <stddef.h>

### 问题2: toybox xxd 不支持 -i 选项
**原因**: embed.sh 使用 xxd -i 生成 C 数组，但 toybox xxd 功能有限
**方案**: 替换 embed.sh 为 Python 脚本生成正确格式

### 问题3: argtable3 缺失
**原因**: 预编译包中没有 argtable3
**方案**: 手动编译 argtable3 静态库

## 验证结果
- 版本输出: astroterm 1.0.9 ✅
- 帮助信息: 正常显示 ✅

## 交付物
- 预编译包: astroterm-1.0.9-r0-ohos-aarch64.tar.gz (706KB)
- 二进制大小: 703KB (stripped)

---
**编译结束**: 2026-05-26 20:21
**最终状态**: built
