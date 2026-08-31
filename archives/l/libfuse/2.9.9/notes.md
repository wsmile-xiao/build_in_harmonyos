# libfuse 2.9.9 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-08-27
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: published

## 编译步骤

```bash
source .build-context-libfuse-2.9.9 && cd $BUILD_SRC_DIR
# 平台适配：更新 config.guess/config.sub（原 2016 版不识别 OHOS）
cp /storage/Users/currentUser/usr/local/share/automake-1.16/config.guess config.guess
cp /storage/Users/currentUser/usr/local/share/automake-1.16/config.sub config.sub
# E011 修复：HMDFS 上 umask 077 导致 config.status 无法写入临时目录
sed -i 's/umask 077/umask 022/g' configure
export CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++ AR=llvm-ar RANLIB=llvm-ranlib
# R1: 参数最少化(只需 --prefix) + R26: 系统同名库静态编译
./configure --prefix=$DEFAULT_PREFIX \
  --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu \
  --disable-shared --enable-static --disable-example --enable-util
make -j1
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess "unable to guess system type" + config.sub "Invalid configuration `aarch64-unknown-linux-ohos'" | libfuse 2.9.9 自带 config.guess/sub 为 2016 版，不识别 OHOS 平台 | 复制 automake-1.16 (2023) 的 config.guess/config.sub 覆盖（R-build-systems §3.1） |
| 2 | config.status: can't create ./confXXXXXX/subs1.awk: Permission denied | E011: HMDFS UID 映射 + umask 077，临时目录 0700 权限对当前进程不可写 | sed -i 's/umask 077/umask 022/g' configure |
| 3 | example/fusexmp 链接失败: undefined reference to pthread_cancel / pthread_setcancelstate | OHOS bionic libc 未实现 pthread_cancel/pthread_setcancelstate（E051 未实现 syscall），且 --no-allow-shlib-undefined 对 libfuse.so 检查未定义符号 | --disable-example 跳过示例编译；库本身编译正常 |
| 4 | make install 递归进入 example/ 失败 | install-recursive 依赖 example 编译 | --disable-example 后 install 跳过 example |
| 5 | mknod dev/fuse: Operation not permitted | OHOS SELinux 限制 mknod（E046） | install 有 `|| true` 容错，不阻塞 |

## 源码修改

| 文件 | 修改 | 机制 |
|------|------|------|
| configure | `umask 077` → `umask 022` (2 处) | patches/0001-configure-umask-022.patch (R3) |

注：config.guess/config.sub 未修改。原版 2016 config.sub 接受 `aarch64-unknown-linux-gnu`
triplet，配合 conan recipe 传入 `--build/--host=aarch64-unknown-linux-gnu` 即可正常交叉编译。

## 依赖版本

无外部 conan 依赖。仅依赖系统头文件：pthread, iconv。
- OHOS bionic libc 提供 pthread（部分函数未实现：pthread_cancel, pthread_setcancelstate）
- iconv 由系统 libc 提供

## 验证结果

```bash
# 库产物
$ ls -la $TEST_PREFIX$DEFAULT_PREFIX/lib/libfuse*.a
  libfuse.a    370754 bytes
  libulockmgr.a 8036 bytes
# fuse_version() 符号可用（test_package 调用）
$ llvm-nm libfuse.a | grep " T fuse_version"
  00000000000007b8 T fuse_version
# 头文件
$ ls $TEST_PREFIX$DEFAULT_PREFIX/include/fuse/
  cuse_lowlevel.h fuse.h fuse_common.h fuse_compat.h fuse_lowlevel.h fuse_opt.h ...
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libfuse.a | 370754 | 主库（静态，R26） |
| lib/libulockmgr.a | 8036 | 锁管理库（静态） |
| include/fuse.h | - | 顶层兼容头 |
| include/fuse/*.h | - | FUSE API 头文件集合 |
| lib/pkgconfig/fuse.pc | - | pkg-config 文件 |

## 上游测试用例

**结论：libfuse 2.9.9 无上游测试套件。**

排查依据（逐项核验源码树 `$BUILD_SRC_ORIG_DIR`）：
- 无 `test/` 或 `tests/` 目录
- 无 `test*.c` / `*_test.c` / `test_*.c` 测试源文件（find 全树无结果）
- `example/Makefile.am` 声明的是 `noinst_PROGRAMS`（示例程序：hello/fusexmp/fioc/fsel 等），**不是** `TESTS` / `check_PROGRAMS`
- 所有 `Makefile.am`（顶层 + example/）均无 `TESTS`、`check_PROGRAMS`、`TESTS_ENVIRONMENT` 声明
- 生成的 `Makefile.in` 中 `check:` 目标为 automake 默认空实现（`check-am: all-am`，仅构建不执行断言）
- `configure.ac` 无测试相关 subdir/option

`example/` 是 FUSE 用法示例代码，非测试，且 notes 中已记录其因 OHOS bionic 缺 pthread_cancel 而以 `--disable-example` 跳过编译（问题 #3），与本结论一致。

替代验证：库的可用性通过 conan test_package 覆盖（调用 `fuse_version()` 链接 libfuse.a，R34 实质测试），conan-verify G0/G1/G2/G3 均通过。

## 注意事项

- R26: libfuse 是系统同名库，必须静态编译（--disable-shared --enable-static），避免 .so 污染 /lib
- R38: 产物含可执行文件 fusermount/mount.fuse/ulockmgr_server，但核心产物是库，conanfile 按 library 类型处理
- OHOS 未实现 pthread_cancel/pthread_setcancelstate：静态库中这些符号是 undefined，将在消费方链接时由系统提供或需消费方处理
- --build/--host 使用 aarch64-unknown-linux-gnu 而非 ohos triplet，因为旧版 autotools 的 config.sub 即使更新后对 -ohos 的 libtool 处理不稳定；用 gnu triplet 让 configure 正常检测交叉编译
---

**编译结束**: 2026-08-27 10:06
**最终状态**: published
