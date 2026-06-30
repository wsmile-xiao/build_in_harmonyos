# cowsql 1.15.9 编译笔记

## 编译状态
状态: success（编译成功）

## 问题与解决

### 问题1: qsort_r 未定义
- 解决: 条件编译 + qsort wrapper

### 问题2: -Wsometimes-uninitialized
- 解决: 初始化变量为 0/NULL

## 预编译包
- cowsql-1.15.9-ohos-aarch64.tar.gz (3.7M)
- cowsql-1.15.9-ohos-aarch64-debug.tar.gz (2.3M)

---
编译结束: 2026-06-04
最终状态: success
