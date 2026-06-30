# mariadb-connector-c 3.4.8 编译笔记

## 编译状态
状态: success（编译成功）

## 问题与解决

### 问题1: ARM64 汇编 X18 寄存器编译错误
- 错误: HarmonyOS 上 X18 是保留寄存器
- 解决: 修改 include/ma_context.h，添加 `&& !defined(__OHOS__)`

### 问题2: PIC 重定位错误
- 错误: R_AARCH64_ADR_PREL_PG_HI21
- 解决: CMake 配置添加 `-DCMAKE_C_FLAGS="-fPIC"`

## 预编译包
- mariadb-connector-c-3.4.8-ohos-aarch64.tar.gz (7.5M)
- mariadb-connector-c-3.4.8-ohos-aarch64-debug.tar.gz (1.4M)

---
编译结束: 2026-06-04
最终状态: success
