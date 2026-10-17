# netdata 1.47.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-04
- 编译器: clang/clang++
- 状态: built

## 编译步骤

（历史记录：2026-06-04 初版探索方案；2026-09-17 已按 AI 检视意见重构为 CMake feature detection，见下方"源码修改"）

1. init-build netdata 1.47.5 (使用本地tarball)
2. 修复CMakeLists.txt: 在Linux检测块中添加OS_OHOS子检测，修复uuid条件判断（将REQUIRED改为QUIET，OS_OHOS时设置UUID_FOUND=True）→ 已重构为 libuuid/arc4random_buf feature detection
3. 修复proc_stat.c: wake_cpu_thread函数中pthread_setaffinity_np/cpu_set_t/CPU_ZERO/CPU_SET用`#ifndef __OHOS__`守卫；cpu_set_t global_cpu_set声明移入#ifndef块内 → 已重构为 `#ifdef HAVE_PTHREAD_SETAFFINITY_NP`
4. cmake configure大量禁用不适用功能（H2O、Cloud、ML、eBPF、Apps、DebugFS、Go、FreeIPMI等）
5. make -j2 → 编译成功
6. make install DESTDIR=$TEST_PREFIX
7. make install（本地安装）
8. verify-build PASS → package → 打包完成

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake uuid条件进入else()分支执行pkg_check_modules(UUID REQUIRED uuid) | CMAKE_SYSTEM_NAME为OHOS/HarmonyOS，但OS_OHOS条件变量在if()中评估为True（实际匹配了elseif OHOS分支），uuid else分支不应被执行。为确保健壮性，将REQUIRED改为QUIET，并在OS_OHOS分支中显式设置UUID_FOUND=True | 修改CMakeLists.txt uuid部分 |
| 2 | proc_stat.c: cpu_set_t/pthread_setaffinity_np编译错误 | OHOS不提供这些Linux特有函数 | 初版用`#ifndef __OHOS__`守卫；2026-09-17 重构为 `#ifdef HAVE_PTHREAD_SETAFFINITY_NP` feature detection |
| 3 | apps.plugin/debugfs.plugin编译失败(libcap) | OHOS无libcap/capabilities | 禁用ENABLE_PLUGIN_APPS和ENABLE_PLUGIN_DEBUGFS |
| 4 | libh2o submodule为空 | tarball不含git submodule | 禁用ENABLE_H2O |

## cmake configure选项

```
-DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local
-DOS_OHOS=True
-DENABLE_ACLK=False -DENABLE_CLOUD=False -DENABLE_ML=False
-DENABLE_PLUGIN_EBPF=False -DENABLE_PLUGIN_GO=False
-DENABLE_PLUGIN_FREEIPMI=False -DENABLE_PLUGIN_CUPS=False
-DENABLE_PLUGIN_SYSTEMD_JOURNAL=False -DENABLE_PLUGIN_XENSTAT=False
-DENABLE_PLUGIN_NFACCT=False -DENABLE_PLUGIN_APPS=False
-DENABLE_PLUGIN_DEBUGFS=False -DENABLE_PLUGIN_LOCAL_LISTENERS=False
-DENABLE_PLUGIN_NETWORK_VIEWER=False
-DENABLE_EXPORTER_MONGODB=False -DENABLE_EXPORTER_PROMETHEUS_REMOTE_WRITE=False
-DENABLE_WEBRTC=False -DENABLE_SENTRY=False -DENABLE_H2O=False
-DUSE_MOLD=False -DCMAKE_BUILD_TYPE=Release
```

## 源码修改（2026-09-17 R8 合规重构：全部改为 CMake feature detection，C 代码零平台宏）

### CMakeLists.txt（0001）
- Linux 检测块添加 OS_OHOS 子检测（`-DOS_OHOS=True` 时报告 OpenHarmony）
- 平台链末端添加 `elseif("${CMAKE_SYSTEM_NAME}" MATCHES "OHOS|OpenHarmony|HarmonyOS")` 分支（设 OS_OHOS/OS_LINUX + `-D_GNU_SOURCE`），**保留** catch-all `else() FATAL_ERROR`（未知平台显式报错）
- 新增 `check_c_source_compiles` 特性检测：HAVE_PTHREAD_SETAFFINITY_NP（setaffinity+getaffinity+cpu_set_t 组合）、HAVE_PTHREAD_SETCANCEL（setcanceltype+setcancelstate）、HAVE_ARC4RANDOM_BUF
- uuid 部分：`pkg_check_modules(UUID QUIET uuid)`，找到则链接 libuuid 并置 HAVE_LIBUUID；找不到则检测 arc4random_buf 兜底，两者皆无时 FATAL_ERROR（不再静默放宽 REQUIRED）

### packaging/cmake/config.cmake.h.in（0003）
- 暴露 HAVE_PTHREAD_SETAFFINITY_NP / HAVE_PTHREAD_SETCANCEL / HAVE_LIBUUID 到 config.h

### src/collectors/proc.plugin/proc_stat.c（0002）
- wake_cpu_thread: cpu_set_t/pthread_setaffinity_np/CPU_ZERO/CPU_SET 用 `#ifdef HAVE_PTHREAD_SETAFFINITY_NP` 守卫
- 调用侧 pthread_getaffinity_np 检查块同样用 `#ifdef HAVE_PTHREAD_SETAFFINITY_NP` 守卫

### src/libnetdata/threads/threads.c（0004）
- pthread_setcanceltype/pthread_setcancelstate 调用用 `#ifdef HAVE_PTHREAD_SETCANCEL` 守卫（OHOS musl 不提供；netdata 1.47.5 源码不使用 pthread_cancel，跳过安全）

### src/libnetdata/os/uuid_generate.c（0005）
- `#if !defined(OS_MACOS) && !defined(HAVE_LIBUUID)` 时改用 arc4random_buf 生成 RFC 4122 v4 UUID（configure 期已验证可用性）

## 依赖版本

- openssl 1.1.1w
- zlib 1.3.1
- liblz4 1.10.0
- libuv 1.52.1
- json-c (pkg-config)
- libyaml 0.1
- sqlite3 (embedded)
- protobuf (pkg-config)

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/usr/sbin/netdata -v
netdata v1.47.5
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| netdata-1.47.5-ohos-aarch64.tar.gz | 55710KB | 预编译包 |

## 注意事项

- ENABLE_H2O禁用（libh2o submodule为空）
- ENABLE_PLUGIN_APPS/DEBUGFS禁用（需要libcap）
- uuid：无 libuuid 时用 arc4random_buf 兜底（HAVE_LIBUUID feature detection）
- threads.c: pthread_setcanceltype/setcancelstate 用 HAVE_PTHREAD_SETCANCEL 守卫（OHOS musl 缺失，netdata 不用 pthread_cancel，跳过安全）
- conanfile.py 依赖引用使用裸 name/version（registry 已无 @ohpcd/stable 通道）
- pcre2/10.40 显式引入：部分 CI worker 有残缺的系统 libpcre2-8.pc（能被发现但链接不到库），conan 版 libpcre2-8.pc 优先，log2journal 可正常启用
---

**编译结束**: 2026-09-17（R8 合规重构后 conan create 复验通过）
**最终状态**: built
