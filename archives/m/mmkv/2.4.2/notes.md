# mmkv 2.4.2 适配笔记

## 软件信息

- 腾讯 MMKV：基于 mmap 的高性能 key-value 存储框架（微信同款）
- 上游：https://github.com/Tencent/MMKV （tag **v2.4.2**，注意带 v 前缀）
- 许可证：BSD-3-Clause
- 语言预检：Core/ 子目录 100% C++（38 个 .cpp）——根目录是多语言 monorepo（Android/iOS/Win32/POSIX/Python/Flutter/KMP/OpenHarmony binding），lang-preflight 对根目录跑会误判 python（Python/setup.py），必须对 Core/ 跑

## 编译环境

- 构建系统: cmake（Core/CMakeLists.txt）
- 编译日期: 2026-09-12
- 编译器: clang/clang++ 15.0.4（OHOS SDK 工具链）
- 状态: built
- 设备: OpenHarmony PC aarch64 本机

## 构建策略（关键决策）

1. **构建目标**：`Core/` 子工程（target `core`，上游写死 STATIC）。
   上游官方 Android/iOS SDK 交付的就是这个静态库（.a）。
2. **平台通路**：OHOS 工具链编译时自动定义 `__OHOS__`，
   `Core/MMKVPredef.h` 据此定义 `MMKV_ANDROID + MMKV_OHOS`，
   走 `MemoryFile_Android.cpp`/`MMKV_Android.cpp`/`InterProcessLock_Android.cpp`
   的 mmap + fcntl 通路，但所有 Android 专有 API（ashmem、
   `__android_log_print`、`AAssetManager`）均被 `#ifndef MMKV_OHOS` 或
   `#elif MMKV_OHOS`（hilog 分支）守卫——**零补丁**。
   Core/CMakeLists.txt 的 `IF(OHOS)` 分支给 aarch64 加
   `-march=armv8+crypto -D__MUSL__`（CRC32/AES 硬件加速 asm 使能）。
3. **为什么不用 POSIX/src 的 SHARED 目标**：`libmmkv.cpp` 是空 TU，
   `-shared` 链接时静态库未被引用成员全部被链接器丢弃，产出空壳
   libmmkv.so（实测 `llvm-nm -D` 只有 _init/_fini）。
   → conan 交付静态库：`libcore.a` 复制为 `libmmkv.a`。
4. **zlib**：交叉 sysroot 下 `find_library(z)` 不解析（zlib-NOTFOUND），
   上游 fallback `MMKV_EMBED_ZLIB=1` 内嵌 `Core/crc32/zlib/crc32.cpp`——
   产物自包含，无外部依赖（W0：sysroot 有 libz.so 但 conan 侧不需要）。
5. **hilog**：`ENABLE_MMKV_LOG`（MMKVLog.h 无条件定义）使
   `MMKVLog_Android.cpp` 的 `MMKV_OHOS` 分支编译 `OH_LOG_Print`，
   消费者需链 `libhilog_ndk.z.so`（sysroot 系统库）。
   recipe `package_info().system_libs = ["hilog_ndk.z", "pthread"]`。

## 编译步骤（探索实录）

```bash
# 1. 下载源码（本地镜像；CI 走 conandata.yml 官方 URL + 自动 fallback）
curl -L -o mmkv-2.4.2.tar.gz \
  "https://ghfast.top/https://github.com/Tencent/MMKV/archive/refs/tags/v2.4.2.tar.gz"

# 2. 从 POSIX 顶层构建（探索期含 demo；conan 配方只建 Core）
cd MMKV-2.4.2/POSIX
cmake .. -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_SYSTEM_NAME=HarmonyOS -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
  -DOHOS=1 -DOHOS_ARCH=arm64-v8a \
  -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++
make -j4   # core.a + libmmkv.so 编译通过

# 3. demo 可执行文件链接需补 hilog（demo 工程未链，属上游 demo 缺陷，不影响库）
/data/service/hnp/bin/clang++ -o UnitTest UnitTest.cpp.obj ../src/Core/libcore.a \
  -L$OHOS_SDK/sysroot/usr/lib/aarch64-linux-ohos -lhilog_ndk.z -lpthread

# 4. 运行（rootDir 必须是可写目录，默认 /tmp/mmkv 只读会 segfault）
export LD_LIBRARY_PATH=$OHOS_SDK/llvm/lib/aarch64-linux-ohos:...
./UnitTest $TMPDIR/mmkv-test     # 20 个测试函数全部通过
./TestThreadLock                 # 上游 CTest 注册项，通过
```

## 上游测试验证（N=21 实测）

| 测试 | 结果 |
|------|------|
| UnitTest：testBool/testInt32/testUInt32/testInt64/testUInt64 | PASS |
| UnitTest：testFloat/testDouble/testString/testBytes/testVector | PASS |
| UnitTest：testRemove/testOversizedKey/testOversizedValue | PASS |
| UnitTest：testExpirationOverflow/testCodedOutputBounds/testExpirationAlignment | PASS |
| UnitTest：testArmCRC32（armv8 CRC32 硬件通路） | PASS |
| UnitTest：testCryptoRandomAndWipe（AES 通路） | PASS |
| UnitTest：testLongDirectoryWalk/testMinimalBackupRestore | PASS |
| CTest TestThreadLock（上游唯一 add_test 注册项） | PASS |

合计 **21/21 = 100%**。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 误判 python | 根目录 monorepo 有 Python/setup.py（判定优先级 manifest>构建系统） | 对 Core/ 子目录重跑 → cpp 100% |
| 2 | POSIX demo 链接报 `undefined symbol: OH_LOG_Print` | demo 可执行文件未链 libhilog_ndk.z.so（上游 demo 工程遗漏） | 手动链接 -lhilog_ndk.z 验证；库本体（静态归档）不受影响 |
| 3 | UnitTest segfault | 默认 rootDir=/tmp/mmkv 只读（E002），mmap 落盘失败 | 传 $TMPDIR 下可写目录 |
| 4 | libmmkv.so 空壳（无导出符号） | libmmkv.cpp 空 TU，-shared 丢弃未引用静态库成员 | 交付静态库 libmmkv.a（官方 SDK 同形态） |
| 5 | conan-init 误判 autotools | URL 模式匹配无 cmake 检测 | 手动重写 conanfile.py（CMakeDeps/CMakeToolchain） |

## 源码修改

**零补丁**。上游 v2.4.2 原始代码，仅构建脚本层面（conanfile.py 的
source() 把 Core/ 提升为源码根 + OHOS/OHOS_ARCH cmake 变量）。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| zlib | 内嵌（MMKV_EMBED_ZLIB=1） | 上游 Core/crc32/zlib/ |
| AES/MD5 | 内嵌 | 上游 Core/aes/openssl/ |
| hilog_ndk.z | 系统库 | OHOS sysroot |
| pthread | 系统库 | OHOS musl |

## 验证结果

```bash
# 本机（OHOS aarch64）实测
$ ./UnitTest $TMPDIR/mmkv-test
test bool: passed
test int32: passed
test uint32: passed
test int64: passed
test uint64: passed
test float: passed
test double: passed
test string: passed
test bytes: passed
test vector: passed
test remove: passed
test oversized key: passed
test oversized value: passed
test coded output bounds: passed
test expiration overflow: passed
test expiration alignment: passed
test arm crc32: passed
test crypto random and wipe: passed
test long directory walk: passed
test minimal backup and restore hardening: passed
EXIT=0

$ ./TestThreadLock
test ThreadLock destruction: passed
EXIT=0
```
---

**编译结束**: 2026-09-12 13:32
**最终状态**: published
