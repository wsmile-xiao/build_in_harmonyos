# gsm 1.0.23 适配笔记

## 编译环境
- 构建系统: Makefile
- 编译日期: 2026-04-24
- 编译器: clang (LLVM)
- 状态: success

## 编译步骤
1. 下载 gsm-1.0.23.tar.gz 并解压
2. 应用补丁 0001-makefile-clang-ln-s.patch
3. `make CC=clang CCFLAGS="-c -O2 -DNeedFunctionPrototypes=1 -Wall -Wno-comment -fPIC" LN="ln -s"`
4. 安装到 TEST_PREFIX

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 使用 gcc 编译 | HM 环境无 gcc | CC=clang |
| 2 | HMDFS 不支持硬链接 | 文件系统限制 | LN="ln -s" |
| 3 | 需要 -fPIC | 静态库链接到共享库 | CCFLAGS 添加 -fPIC |

## 源码修改
| 文件 | 修改内容 | 是否已生成补丁 |
|------|----------|----------------|
| Makefile | CC=gcc→clang, 加 -fPIC, LN=ln -s | ✅ 0001-makefile-clang-ln-s.patch |

## 依赖版本
- 无依赖

## 验证结果
- toast/untoast/tcat 工具功能正常 ✅

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| gsm-1.0.23-ohos-aarch64.tar.gz | 174KB | 主包 |
| gsm-1.0.23-ohos-aarch64-debug.tar.gz | 31KB | 调试符号 |
