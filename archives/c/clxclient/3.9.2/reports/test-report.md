# clxclient 3.9.2 测试报告

> **项目**: clxclient
> **测试日期**: 2026-08-31
> **测试环境**: HarmonyOS PC aarch64（OHOS clang 15, ohos-aarch64 profile）
> **测试类型**: 本地 CI 模拟（ci/conan/build_and_test.sh）+ 消费者 test_package

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 1 | 100% |
| 通过 (PASS) | 1 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%**

---

## 二、测试结论

### 2.1 总体评价

✅ **通过** — clxclient/3.9.2 共享库在 OHOS aarch64 上编译成功，`conan create` 完整通过
（含 test_package 消费者测试），本地 CI 模拟（build_and_test.sh）全部门禁 PASS。

### 2.2 主要问题

无。

### 2.3 可用功能清单

```
✅ 库构建: libclxclient.so.3.9.2（ELF64/AArch64, SONAME=libclxclient.so.3）
✅ 头文件: clxclient.h 随包安装
✅ X_resman 资源库 API: XrmParseCommand 命令行资源 + get/getb 往返校验
✅ 链接链: libclxclient.so -> .so.3 -> .so.3.9.2 完整
```

### 2.4 已知限制

1. 上游 3.9.2 无任何测试目标/测试目录（`make check` 报 No rule），已如实声明
2. X11 图形控件类（窗口/按钮等）需显示服务器，未在无显示 CI 环境实测（属运行时能力，非编译缺陷）

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| conan create | 从干净源码构建 libclxclient.so.3.9.2 | ✅ PASS |
| test_package/test_clxclient | 链接 clxclient 并调用 X_resman（XrmParseCommand 喂入 -geometry/-title，get/getb 往返校验，无 X display 依赖） | ✅ PASS |
| 本地 CI 模拟（build_and_test.sh） | JC/L0/L1/L4/L5 全 PASS，Pass rate 100% (1/1) | ✅ PASS |

### 3.2 失败的测试

无。

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| L2 smoke test | 库类型（无 bin/ 目录），CI 自动 skip |

---

## 四、关键问题分析

### 问题1: OHOS loader 需要显式 DT_NEEDED

- **现象**: 初版链接缺 `-lclthreads`，运行 test_package 时 `_ZN8P_threadC2Ev` 等符号 not found
- **根因**: 上游 Makefile `CLXCLIENT_DEP = -lpthread -lXft -lX11` 未链 clthreads，glibc 的
  全局符号回退在 OHOS loader 上不可用
- **解决**: 补丁将 `CLXCLIENT_DEP` 改为 `-lclthreads -lpthread -lXft -lX11`，使
  libclxclient.so.3 的 DT_NEEDED 包含 libclthreads.so.2

### 问题2: OHOS 运行时依赖库加载

- **现象**: test_package 直接运行时 `dlopen libfontconfig.so.1` 报 Permission denied
- **根因**: conan 缓存 .so 未经 OHOS ELF 签名，loader 拒绝加载
- **解决**: test_package 采用 libxft 同款 OHOS 运行时 staging——复制完整运行时闭包 + 逐个
  binary-sign-tool 签名 + LD_LIBRARY_PATH 指向 staging 目录 + 校验 RPATH
