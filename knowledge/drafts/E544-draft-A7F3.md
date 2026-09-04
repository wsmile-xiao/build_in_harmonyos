# E544-draft-A7F3 — musl libc（OHOS）与 glibc 差异三连

## 错误面
- **触发**：clang/make/运行时
- **阶段**：compilation/runtime
- **签名**：`invalid output constraint '=a'` /
  `use of undeclared identifier 'NETDB_INTERNAL'` / h_errno 分支语义错

## 识别
- severity: 2（🟡medium，编译期可定位但组合出现时排查面广）
- category: musl, libc, portability, compat, ohos, headers

## 诊断
OHOS 使用 musl libc，与 glibc 的差异三连：

1. **时钟**：x86 `rdtsc/rdtscp` TSC 内联汇编在 aarch64 无效，
   musl 也无 glibc 的 vdso 兜底交叉引用
2. **netdb 宏**：`NETDB_INTERNAL` 是 glibc 专用枚举，musl 无
3. **h_errno/gethostbyname_r**：错误分支不能比较 glibc 专用常量

## 方案

| 差异 | musl 移植方案 |
|------|--------------|
| TSC 时钟 | `clock_gettime(CLOCK_MONOTONIC)`（或 gettimeofday 换算 ms） |
| NETDB_INTERNAL | `#ifndef NETDB_INTERNAL #define NETDB_INTERNAL (-1) #endif` |
| h_errno 分支 | 按 musl 返回码判断，不比较 glibc 枚举 |

参考补丁：`archives/l/libco/1.0/patches/0001-co_hook_sys_call.cpp.patch`

## 禁止
- ❌ 源码裸用 `rdtscp/rdtsc`——aarch64 clang 直接编译失败
- ❌ 源码裸用 `NETDB_INTERNAL` 不带 fallback——undeclared identifier
