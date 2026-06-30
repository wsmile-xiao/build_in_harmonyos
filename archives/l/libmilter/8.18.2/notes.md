# libmilter 8.18.2 适配笔记

## 编译环境
- 构建系统: sendmail Build (非 autotools)
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 平台: HarmonyOS HongMengKernel 1.12.0 aarch64
- 状态: published

## 编译步骤

sendmail 项目使用自定义 Build 系统，不是标准的 autotools。

### 1. 配置平台支持
创建 `devtools/OS/HarmonyOS` 配置文件，基于 Linux 配置：
- 定义平台特定的编译选项
- 添加 `HASSTRERROR` 和 `ERRLIST_PREDEFINED` 宏（musl libc 兼容）

### 2. 编译
```bash
cd libmilter
./Build
```

Build 脚本会自动：
- 检测平台（基于 devtools/OS 目录）
- 生成 Makefile
- 编译生成 libmilter.a 静态库

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | musl sys_errlist 兼容性 | musl libc 不提供 sys_errlist/sys_nerr | 修改 libsm/strerror.c，添加 __OHOS__/__MUSL__ 守卫，使用标准 strerror() |
| 2 | 静态库签名 | 静态库是 ar 格式，非 ELF | 无需签名，仅动态库和可执行文件需要 ELF 签名 |

## 源码修改

### 补丁 1: devtools/OS/HarmonyOS
- 类型: 平台配置
- 守卫: 无（平台识别文件）
- 内容: 定义 HarmonyOS 平台的编译选项和宏

### 补丁 2: libsm/strerror.c
- 类型: musl 兼容性修复
- 守卫: `#if defined(__OHOS__) || defined(__MUSL__)`
- 内容: 使用标准 strerror() 函数替代 sys_errlist 数组访问

## 依赖版本

- 无外部依赖（libmilter 是独立的静态库）

## 验证结果

```bash
# 检查静态库
ar -t libmilter.a
# 输出: main.o engine.o listener.o worker.o handler.o comm.o smfi.o signal.o sm_gethost.o monitor.o errstring.o strl.o

# 验证头文件
ls include/libmilter/
# 输出: libmilter.h mfapi.h mfdef.h milter.h
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libmilter-8.18.2-ohos-aarch64.tar.gz | 10KB | 预编译包（静态库 + 头文件） |
| libmilter.a | 78KB | 静态库 |
| libmilter.h, mfapi.h, mfdef.h, milter.h | - | 头文件 |

## 注意事项

1. **构建系统**: sendmail 使用 Build 系统，不是 autotools，无需 configure 步骤
2. **静态库**: libmilter 编译为静态库（libmilter.a），不是动态库
3. **签名**: 静态库无需 ELF 签名，仅动态库和可执行文件需要
4. **补丁**: 只修改源文件（devtools/OS 和 libsm/），不修改生成文件（obj 目录）