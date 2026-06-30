# netdata 1.47.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-04
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. init-build netdata 1.47.5 (使用本地tarball)
2. 修复CMakeLists.txt: 在Linux检测块中添加OS_OHOS子检测，修复uuid条件判断（将REQUIRED改为QUIET，OS_OHOS时设置UUID_FOUND=True）
3. 修复proc_stat.c: wake_cpu_thread函数中pthread_setaffinity_np/cpu_set_t/CPU_ZERO/CPU_SET用`#ifndef __OHOS__`守卫；cpu_set_t global_cpu_set声明移入#ifndef块内
4. cmake configure大量禁用不适用功能（H2O、Cloud、ML、eBPF、Apps、DebugFS、Go、FreeIPMI等）
5. make -j2 → 编译成功
6. make install DESTDIR=$TEST_PREFIX
7. make install（本地安装）
8. verify-build PASS → package → 打包完成

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake uuid条件进入else()分支执行pkg_check_modules(UUID REQUIRED uuid) | CMAKE_SYSTEM_NAME为OHOS/HarmonyOS，但OS_OHOS条件变量在if()中评估为True（实际匹配了elseif OHOS分支），uuid else分支不应被执行。为确保健壮性，将REQUIRED改为QUIET，并在OS_OHOS分支中显式设置UUID_FOUND=True | 修改CMakeLists.txt uuid部分 |
| 2 | proc_stat.c: cpu_set_t/pthread_setaffinity_np编译错误 | OHOS不提供这些Linux特有函数 | 用`#ifndef __OHOS__`守卫，移入类型声明 |
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

## 源码修改

### CMakeLists.txt
- Linux检测块添加OS_OHOS子检测（cmake -DOS_OHOS=True时启用-D__OHOS__）
- uuid部分：OS_OHOS时设置UUID_FOUND=True/UUID_LIBRARIES=""，else分支改为QUIET而非REQUIRED

### src/collectors/proc.plugin/proc_stat.c
- wake_cpu_thread: cpu_set_t/pthread_setaffinity_np/CPU_ZERO/CPU_SET用`#ifndef __OHOS__`守卫
- cpu_set_t global_cpu_set声明移入`#ifndef __OHOS__`块内

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
- uuid使用内置arc4random_buf实现（__OHOS__分支）
- threads.c已有`#ifndef __OHOS__`守卫（pthread_cancel）
---

**编译结束**: 2026-06-04 03:51
**最终状态**: built
