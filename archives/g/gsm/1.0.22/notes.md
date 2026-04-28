# gsm 1.0.22 适配笔记

## 编译环境
- 构建系统: Makefile
- 编译日期: 2026-04-22
- 编译器: clang (LLVM)
- 状态: partial

## 编译步骤
1. 下载 gsm-1.0.22.tar.gz 并解压
2. 修改 Makefile：CC=clang, CCFLAGS 加 -fPIC
3. `make`
4. 手动安装到 TEST_PREFIX

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 使用 gcc | HM 无 gcc | 修改 CC=clang |

## 依赖版本
- 无依赖

## 注意事项
- 推荐使用 1.0.23 版本（有完整补丁）
