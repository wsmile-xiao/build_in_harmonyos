# bdw-gc 8.2.6 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-05
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
source .build-context-bdw-gc-8.2.6
cd $BUILD_SRC_DIR
export CONFIG_SHELL=/data/service/hnp/bin/bash
export SHELL=/data/service/hnp/bin/bash

# Apply existing HarmonyOS platform patches
for p in $BUILD_ARCHIVE_DIR/patches/*.patch; do patch -p1 < "$p"; done

# E011 fix: HMDFS umask 077 causes Permission denied in config.status
sed -i 's/umask 077/umask 022/g' configure

# Configure
$CONFIG_SHELL ./configure --prefix=$DEFAULT_PREFIX

# Build
make -j2

# Install to staging
make install DESTDIR=$TEST_PREFIX

# Test
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status: Permission denied creating subs1.awk | E011: HMDFS umask 077 creates dirs with 0700 perms, process uid != file owner uid | sed -i 's/umask 077/umask 022/g' configure |
| 2 | undefined reference: pthread_setcancelstate | HarmonyOS musl libc lacks pthread_setcancelstate; CANCEL_SAFE enabled on UNIX_LIKE+THREADS | Patch gcconfig.h: add `&& !defined(__OHOS__)` to CANCEL_SAFE condition |
| 3 | undefined reference: pthread_cancel | HarmonyOS musl libc lacks pthread_cancel; GC_HAVE_PTHREAD_EXIT auto-defined for Linux-like | Patch gc_config_macros.h: add `&& !defined(__OHOS__)` to GC_HAVE_PTHREAD_EXIT condition |

## 源码修改

| 文件 | 修改内容 |
|------|----------|
| config.guess | 添加 HarmonyOS 平台检测 (aarch64-unknown-linux-ohos) |
| config.sub | 添加 HarmonyOS 平台识别 |
| configure | umask 077 → umask 022 (E011 HMDFS fix) |
| include/gc_config_macros.h | 排除 __OHOS__ 从 GC_HAVE_PTHREAD_EXIT 条件 |
| include/private/gcconfig.h | 排除 __OHOS__ 从 CANCEL_SAFE 条件 |

## 依赖版本

无外部依赖。bdw-gc 使用内嵌的 libatomic_ops。

## 验证结果

```
make check: 16/16 tests passed
conan-verify: G1-G4, L2/L4/L5 all PASS
```

## 注意事项

- HarmonyOS musl libc 不提供 pthread_setcancelstate 和 pthread_cancel 函数
- 这两个函数在 bdw-gc 中由 CANCEL_SAFE 和 GC_HAVE_PTHREAD_EXIT 宏控制
- 通过在条件中排除 __OHOS__ 来禁用这些代码路径，功能不受影响
  （HarmonyOS 不支持线程取消，no-op 替代是正确行为）
---

**编译结束**: 2026-08-06 00:13
**最终状态**: built
