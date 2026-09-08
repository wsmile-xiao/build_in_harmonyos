# libcap-ng 0.8.5 编译记录

## 构建信息
- **日期**: 2026-09-05
- **平台**: HarmonyOS aarch64 (HongMeng Kernel)
- **编译器**: clang 15.0.4
- **源码**: https://github.com/stevegrubb/libcap-ng/archive/refs/tags/v0.8.5.tar.gz

## 编译过程

### 问题 1: GitHub archive 缺少 configure 脚本
- **问题描述**: GitHub archive tarball 只有 configure.ac，没有预生成的 configure 脚本
- **环境限制**: 系统有 autoconf 2.72 但无 automake/libtool（autoreconf 失败）
- **解决方案**: 直接编译源文件，在 build() 中生成 config.h

### 问题 2: 上游 lib_test 失败
- **问题描述**: lib_test 在 i=40 时 SIGABRT
- **根因**:
  - `/proc/sys/kernel/cap_last_cap` 在 OHOS 上不存在
  - test 的 `get_last_cap()` 返回 `CAP_LAST_CAP=40`（来自内核头文件）
  - 库的 `init_lib()` 通过 `prctl(PR_CAPBSET_READ)` 二分搜索检测到 `last_cap=39`
  - `cap_valid(40)` = `40 <= 39` = false → `capng_update` 返回 -1
- **影响**: 仅影响上游 lib_test，不影响库功能
- **thread_test**: 通过

### 问题 3: 进程默认 capabilities
- OHOS 进程有默认 capabilities: 0x2a (dac_override, fowner, kill)
- 标准 Linux 非 root 进程通常无 capabilities
- 库的 `capng_have_capabilities()` 在 state < INIT 时调用 `capng_get_caps_process()` 覆盖已清除的数据

## 构建产物
- libcap-ng.so.0.0.1 / libcap-ng.a (库)
- libdrop_ambient.so.0.0.0 / libdrop_ambient.a (ambient capabilities 库)
- pscap, netcap, filecap, captest (实用工具)
- cap-ng.h (头文件)

## 编译参数
- CFLAGS: -fPIC -DPIC -O2 -W -Wall -Wshadow -Wundef -D_GNU_SOURCE
- LDFLAGS: -Wl,-z,relro

## 依赖
- 无 conan 依赖
- 系统级依赖: linux/capability.h, pthread, OHOS SDK sysroot

## Conan 配方
- 构建系统: custom (直接编译，不使用 autotools)
- 在 build() 中生成 config.h
- 支持 shared/static 选项
- 导出 CMake target: libcap-ng::libcap-ng

## 测试声明
- 上游 lib_test: 平台问题（last_cap mismatch），不阻塞
- 上游 thread_test: 通过
- test_package: 自定义测试覆盖 clear/fill/update/have_capability/text conversion/save-restore/updatev
---

**编译结束**: 2026-09-05 02:16
**最终状态**: built
