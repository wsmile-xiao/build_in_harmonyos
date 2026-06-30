# foma 0.10.0 编译笔记

**日期**: 2026-06-16
**状态**: built

## 编译过程

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✓ | 下载源码成功 |
| Step 2 configure | ✓ | CMake 配置成功 |
| Step 3 make | ✓ | 编译成功 |
| Step 4 install | ✓ | DESTDIR 安装成功 |
| Step 5 test | ✓ | 6/6 测试通过 |
| Step 6 package | ⏳ | 待完成 |

## 问题与解决方案

### 问题 1: readline 未安装
- **现象**: configure 检测不到 readline
- **原因**: readline 8.2 归档中无预编译包，config.status 创建临时目录权限问题
- **解决**: 修改 CMakeLists.txt 使 readline 为可选依赖，添加 NO_READLINE 支持

### 问题 2: zlib 路径检测失败
- **现象**: CMake find_path 无法找到 zlib.h
- **原因**: 默认查找路径不包含 ~/usr/local
- **解决**: 修改 CMakeLists.txt 添加自定义路径搜索

### 问题 3: getopt.h 检测失败
- **现象**: GETOPT_INCLUDE-NOTFOUND 导致编译失败
- **原因**: 系统无 getopt.h 头文件
- **解决**: 修改 CMakeLists.txt 使 getopt.h include 为可选

### 问题 4: readline 相关变量编译错误
- **现象**: 使用 rl_* 变量时编译失败
- **原因**: NO_READLINE 定义后这些变量不存在
- **解决**: 在 foma.c 中添加条件编译块

## 功能测试
- 所有 tests/ 目录中的测试脚本通过
- foma -q -f test-*.foma 全部执行成功
- flookup 和 cgflookup 正常工作

## 已知限制
- 无 readline 交互式编辑支持（使用 fgets 替代）
- 不影响核心功能和库使用

---
**编译结束**: 2026-06-16 16:10
**最终状态**: built