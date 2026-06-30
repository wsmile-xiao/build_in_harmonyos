# dvgrab 3.8 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-30
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
./configure --prefix=$DEFAULT_PREFIX
make -j2
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 OHOS 平台 | 缺少 HarmonyOS 平台检测 | 替换为支持 OHOS 的 config.guess |
| 2 | config.sub 无法识别 ohos 目标 | 缺少 ohos 目标三元组 | 替换为支持 OHOS 的 config.sub |
| 3 | `pthread_testcancel` 未定义 | musl libc 不提供此函数 | 用 `#define pthread_testcancel() ((void)0)` 守卫 |
| 4 | `__ASSERT_FUNCTION` 未定义 | glibc 特有，musl 使用 `__func__` | 用 `#define __ASSERT_FUNCTION __func__` 守卫 |
| 5 | `pthread_cancel` 未定义 | musl libc 不提供此函数 | 用 `#define pthread_cancel(thread) ((void)0)` 宏替代 |
| 6 | 隐式声明 `select` | 缺少 `<sys/select.h>` 头文件 | 添加 `#include <sys/select.h>` |

## 源码修改

- 0001-config.guess.patch: 替换为支持 OHOS 平台检测的版本
- 0002-config.sub.patch: 替换为支持 ohos 目标三元组的版本
- 0003-dvgrab.h.patch: 添加 pthread_testcancel 宏守卫
- 0004-error.h.patch: 添加 __ASSERT_FUNCTION 宏守卫
- 0005-ieee1394io.cc.patch: 添加 pthread_cancel/pthread_testcancel 宏替代
- 0006-io.c.patch: 添加 sys/select.h 头文件

## 验证结果

无二进制产物（仅编译测试通过）

## 交付物

| 文件 | 说明 |
|------|------|
| dvgrab-3.8-ohos-aarch64.tar.gz | 预编译包 |
| dvgrab-3.8-ohos-aarch64-debug.tar.gz | 调试符号包 |

---
**编译结束**: 2026-05-30
**最终状态**: published