# jthread 1.3.3 适配笔记

## 编译环境

- 构建系统: CMake
- 编译日期: 2026-08-14
- 编译器: Clang 15.0.4
- 目标平台: aarch64-unknown-linux-ohos
- 状态: published

## 编译步骤

jthread 1.3.3 使用 CMake 构建。默认生成静态库，Conan 配方通过 `JTHREAD_COMPILE_STATIC_ONLY=ON` 控制静态构建。

由于当前环境使用 CMake 4.1，而上游源码声明 `cmake_minimum_required(VERSION 3.0)`，配置阶段增加 `CMAKE_POLICY_VERSION_MINIMUM=3.5`。

OHOS 构建时自动选择可用的 clang/clang++ 编译器，并使用 pthread 线程实现。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.1 配置失败 | 上游最低 CMake 版本为 3.0 | 设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 2 | Conan profile 编译器路径在本机不存在 | CI 与本地 clang 安装路径不同 | 配方运行时自动查找 clang/clang++ |
| 3 | 预下载源码 URL 被截断 | CI URL 提取会在文件名中的连字符处截断 | 将连字符编码为 `%2D` 并处理 file URL 编码 |
| 4 | OHOS 不提供 pthread_cancel | 平台线程接口差异 | 上游自动启用 `JTHREAD_SKIP_PTHREAD_CANCEL`，无需源码补丁 |

## 源码修改

无源码补丁。jthread 1.3.3 原始源码可直接使用 OHOS pthread 实现完成编译。

## 依赖版本

无额外 Conan 三方依赖，OHOS 平台使用系统 pthread。

## 验证结果

`python3 scripts/ohc-run.py conan-verify jthread 1.3.3`

G1、G0、G2、G3 均通过，VERIFY_RC=0。

`zsh ci/conan/build_and_test.sh archives/j/jthread/1.3.3`

L0、L1、L4、L5 均通过，L2 因无 bin 目录正常跳过。

功能测试：3 个独立 test_package 用例全部通过

三个新增功能测试均执行通过；构建流水线 Success: 1，Failed: 0，Pass rate: 100.0%。

test_package 包含 3 个独立测试程序，分别验证线程生命周期、线程返回值和多个线程并发执行。L1e 破坏性负向测试通过。

## 主要交付物

- `include/jthread/jmutex.h`
- `include/jthread/jthread.h`
- `include/jthread/jmutexautolock.h`
- `include/jthread/jthreadconfig.h`
- `lib/libjthread.a`
- `lib/cmake/JThread/JThreadConfig.cmake`
- `lib/pkgconfig/jthread.pc`

## 注意事项

`pthread_cancel` 在 OHOS 上不可用，但上游 CMake 会自动检测并禁用对应逻辑，不影响 jthread 基本线程功能。

---

**编译结束**: 2026-08-14 11:18
**最终状态**: published
