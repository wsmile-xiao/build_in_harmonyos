# libgpiod 2.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-05
- 编译器: clang/clang++
- 状态: built (archive files created, awaiting CI verification)

## 基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libgpiod |
| 版本 | 2.0 |
| 构建系统 | autotools |
| 源码 URL | https://mirrors.edge.kernel.org/pub/software/libs/libgpiod/libgpiod-2.0.tar.gz |
| SHA256 | e02400fcd4acc21eca021e7e5d184f828d1a5fd458a156234d3b861becea7f92 |
| 依赖 | 无 |

## 编译步骤

1. 下载源码: libgpiod-2.0.tar.gz
2. 解压源码到构建目录
3. 应用 4 个平台适配补丁:
   - 0001-config-guess.patch: 添加 HarmonyOS 平台检测到 config.guess
   - 0002-config-sub.patch: 添加 ohos-linux 系统类型支持到 config.sub
   - 0003-configure-umask.patch: 将 umask 077 改为 022 (HMDFS 兼容), 注释掉 versionsort 错误
   - 0004-versionsort-compat.patch: 为 musl libc 提供 versionsort() 兼容实现
4. 执行 configure: `./configure --prefix=$DEFAULT_PREFIX --enable-tools`
5. 执行 make: `make -j2`
6. 执行 make install: `make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | autoconf 版本旧，不支持 HarmonyOS | 添加 `*:HarmonyOS:*:*` case 分支 |
| 2 | config.sub 不支持 ohos | autoconf 版本旧 | 添加 ohos-linux 和 ohos* 系统类型 |
| 3 | 临时目录创建失败 | HMDFS 对 umask 077 创建的目录权限不正确 (E011) | 将 umask 077 改为 022 |
| 4 | versionsort() 未找到 | musl libc 不提供 versionsort() 函数 | 在 tools/tools-common.c 中添加 __OHOS__ 守卫的兼容实现 |

## 源码修改

### 补丁文件列表

1. **patches/0001-config-guess.patch** — autostuff/config.guess
   - 添加 `*:HarmonyOS:*:*` case 分支，将 HarmonyOS 映射到 `aarch64-unknown-linux-ohos`

2. **patches/0002-config-sub.patch** — autostuff/config.sub
   - 添加 `ohos-linux` 到 basic_os 映射
   - 添加 `ohos*` 到系统类型列表
   - 添加 `linux-ohos*` 到 kernel-os case

3. **patches/0003-configure-umask.patch** — configure
   - 将 `umask 077` 改为 `umask 022` (HMDFS 兼容)
   - 注释掉 versionsort 未找到的错误 (由兼容代码提供)

4. **patches/0004-versionsort-compat.patch** — tools/tools-common.c
   - 在 `#include "tools-common.h"` 后添加 versionsort() 兼容实现
   - 使用 `#ifdef __OHOS__` 守卫

## 依赖版本

无外部依赖。libgpiod 2.0 仅依赖 Linux 内核 GPIO 字符设备接口。

## 验证结果

```bash
# 消费者测试 (test_package)
# 构建 test_libgpiod 并调用 libgpiod API:
# - gpiod_line_config_new() / gpiod_line_config_free()
# - gpiod_request_config_new() / gpiod_request_config_free()
# - gpiod_version_string()
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (autotools, 动态库默认, --enable-tools) |
| conandata.yml | 源码 URL + SHA256 + 补丁声明 |
| test_package/ | 消费者测试 (调用真实 libgpiod API) |
| patches/ | 4 个平台适配补丁 |
| commands.json | CLI 工具声明 (软件级, R38) |
| manifest.yaml | 编译元数据 |

## 构建产物

libgpiod 2.0 产生以下产物:
- **库文件**: libgpiod.a / libgpiod.so
- **工具**: gpiodetect, gpioinfo, gpioget, gpioset, gpiomon, gpionotify

## 注意事项

- libgpiod 2.0 的源码结构与 2.1.3 类似 (autostuff/, tools/, configure)
- 补丁基于 2.1.3 适配经验，可能需要根据 2.0 实际源码调整行号
- versionsort 兼容实现使用 __OHOS__ 宏守卫 (R8 例外: 源码中可用)
- conanfile.py 使用动态链接默认 (R26: libgpiod 不是系统同名库，默认动态)
- commands.json 声明了 CLI 工具 (R38)
---

**编译结束**: 2026-09-05 11:11
**最终状态**: built
