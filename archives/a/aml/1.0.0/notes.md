# aml 1.0.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-24
- 编译器: clang/clang++ (OHOS SDK 15.0.4)
- 状态: published

## 编译步骤

```bash
# init-build: 官方 tag v1.0.0 源码下载（codeload.github.com，SHA-256 已核验）
# lang-preflight: 通过（detected=c，任务语言 cpp 兼容族）
meson setup builddir --prefix=$DEFAULT_PREFIX
ninja -C builddir
DESTDIR=$TEST_PREFIX meson install -C builddir
# examples 验证（examples=true）: ticker 例程实际运行并输出 "tick 1!"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `pthread_setcancelstate` 在链接期 undefined symbol | OHOS libc 不提供该符号（头文件无声明、库中无定义，与 Android 类似） | meson 特性检测 `cc.has_function('pthread_setcancelstate')` 定义 `HAVE_PTHREAD_SETCANCELSTATE` 宏；thread-pool.c 中 `#if !defined(__ANDROID__) && defined(HAVE_PTHREAD_SETCANCELSTATE)` 守卫（0002 补丁），无平台宏硬编码（0001 补丁） |
| 2 | meson/clang 无法解析 PATH 中的裸命令 | 设备 python3 subprocess posix_spawn 不搜索 PATH | 使用绝对路径 CC/CXX/AR/RANLIB/NM/STRIP 注入环境 |

## 源码修改

- `0001-meson.build.patch`: 新增 pthread_setcancelstate 特性检测，仅在可用时注入 `-DHAVE_PTHREAD_SETCANCELSTATE`
- `0002-src-thread-pool.c.patch`: worker_fn 中 pthread_setcancelstate 调用加特性检测守卫（保留上游 __ANDROID__ 守卫）

## 依赖版本

- 无外部 Conan 依赖；仅系统 libc/pthreads/librt
- 构建期工具: meson 1.11.1、ninja 1.13.1、clang 15.0.4

## 验证结果

```bash
# 1) 库编译链接通过（meson + ninja, libaml.so.1.0.0）
# 2) 上游 examples 实际运行: ticker 输出 "tick 1!"（事件循环正常）
# 3) 上游测试: meson test --list 无注册测试（无 tests/ 目录、无 test 目标），
#    examples 为示例程序非测试用例 → source_declared_total=0
# 4) test_package 消费者测试（test.c）: 调用公共 API aml_new/aml_ticker_new/
#    aml_start/aml_run/aml_exit，ticker 回调触发计数 >0 后正常退出 → PASS
```
---

**编译结束**: 2026-09-24 18:58
**最终状态**: published
