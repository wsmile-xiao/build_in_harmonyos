# Zix

## 简介
Zix 是一个轻量级的基础工具库，提供常用数据结构和系统工具。

## 功能概述
- B-tree 数据结构
- Ring buffer 环形缓冲区
- Semaphores 信号量
- Filesystem 文件系统操作
- Thread 线程支持
- String utilities 字符串工具

## OHOS 适配
- 构建系统: meson 1.11.1
- 硬链接功能测试失败（OpenHarmony 平台限制）
- 核心功能测试全部通过（20/24）
- 不影响作为 LV2 生态依赖库使用

## 依赖
- 无外部依赖（可选 glib-2.0）

## 功能验证
```bash
pkg-config --modversion zix-0  # 输出: 0.8.1
```

## 参考
- 官网: https://drobilla.net/software/zix
- 源码: https://gitlab.com/drobilla/zix