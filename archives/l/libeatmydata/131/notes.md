# libeatmydata 131 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-03
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
cd $BUILD_SRC_DIR
# 需先 bootstrap (GitHub tarball 无 configure 脚本)
sh hints/bootstrap.sh
./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | driver Step3 configure RC=127 | config.status HMDFS mktemp 问题 | 实际 configure 已成功，driver 误报 |
| 2 | make RC=2 mkfifo + no makefile | GNU make jobserver mkfifo 权限问题 | 手动 make -j1 成功 |
| 3 | tst-cancel4 link fail: pthread_cancel | musl 无 pthread_cancel | 源码加 #ifdef __OHOS__ stub |
| 4 | test_run.sh not found | /bin/bash 不存在 + strace 不可用 | 手动直接运行测试程序 |
| 5 | tst-key4 FAIL | musl PTHREAD_KEYS_MAX=128 vs glibc 1024 | 记录为平台限制，非库 bug |

## 源码修改

- `libeatmydata/libeatmydata.c`: 添加 `#ifndef __OHOS__` 守卫，在 OHOS 上跳过 `pthread_testcancel()` 调用和 `#pragma weak pthread_testcancel` 声明
- `libeatmydata/test/tst-cancel4.c`: 添加 `#ifdef __OHOS__` stub，在 OHOS 上直接返回 0 (SKIP)

## 依赖版本

无外部依赖

## 验证结果

### 原始测试套件（安装路径 LD_PRELOAD）

- eatmydatatest: ✅ PASS（O_SYNC/O_DSYNC 剥离 + fsync/fdatasync/msync 拦截）
- eatmydatatest_largefile: ✅ PASS（大文件 O_SYNC/O_DSYNC 剥离）
- fsynctest: ✅ PASS
- syncfstest: ✅ PASS
- fcntltest: ✅ PASS
- tst-invalidfd: ✅ PASS
- tst-cancel4: ⏭️ SKIP (OHOS stub)
- tst-key4: ❌ FAIL (musl PTHREAD_KEYS_MAX 限制，非库 bug)

### LD_PRELOAD 拦截机制详细验证（2026-06-03）

使用自定义测试程序对比有无 LD_PRELOAD 的行为差异：

| 功能 | 无 LD_PRELOAD | 有 LD_PRELOAD | 结论 |
|------|--------------|--------------|------|
| fsync(valid_fd) | 0 (真实同步) | 0 (拦截) | ✅ |
| fsync(invalid_fd) | -1 EBADF | -1 EBADF | ✅ 错误处理正确 |
| fdatasync(valid_fd) | 0 | 0 | ✅ |
| fdatasync(invalid_fd) | -1 EBADF | -1 EBADF | ✅ |
| msync(NULL,1,MS_SYNC) | -1 ENOMEM | 0 | ✅ 拦截生效 |
| open(O_SYNC) → fcntl(F_GETFL) | 含 O_SYNC | 不含 O_SYNC | ✅ 剥离生效 |
| open(O_DSYNC) → fcntl(F_GETFL) | 含 O_DSYNC | 不含 O_DSYNC | ✅ 剥离生效 |

eatmydata wrapper 命令实战验证：
- eatmydata + cp: ✅ PASS
- eatmydata + touch: ✅ PASS
- LD_PRELOAD 环境变量传递: ✅ PASS

**核心结论**: LD_PRELOAD 机制在 OHOS 上完全正常工作，所有拦截功能（fsync/fdatasync/msync/syncfs/open O_SYNC/O_DSYNC 剥离）均已验证通过。

### 补丁守卫确认

- 0001-libeatmydata-libeatmydata.c.patch: #ifdef __OHOS__ 守卫 ✅ 已确认（6处）
- 0002-libeatmydata-test-tst-cancel4.c.patch: #ifdef __OHOS__ 守卫 ✅ 已确认（2处）

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libeatmydata.so | 31KB | LD_PRELOAD 共享库 |
| libeatmydata.a | 10KB | 静态库 |
| eatmydata | 脚本 | LD_PRELOAD wrapper 命令 |
| eatmydata.sh | 脳本 | LD_PRELOAD shell 集成 |
| libeatmydata-131-ohos-aarch64.tar.gz | ~98KB | 预编译包（stripped + ELF signed） |

## 注意事项

- LD_PRELOAD 是 Linux/OHOS 特定机制，此库不适用于 Windows
- tst-cancel4 测试在 OHOS 上被 stub 跳过（pthread_cancel 不可用）
- tst-key4 测试在 musl 上失败（PTHREAD_KEYS_MAX 限制，非库缺陷）
- test_run.sh 在 OHOS 上不可用（需 /bin/bash + strace）
- GitHub tarball 缺少 configure 脚本，需先运行 hints/bootstrap.sh

---
**编译结束**: 2026-06-03
**最终状态**: published
---

**编译结束**: 2026-06-03 14:29
**最终状态**: published
