# autofs 5.1.9 编译笔记

## 编译日期
2026-08-23

## 编译环境
- OpenHarmony (HarmonyOS Kernel 1.12.0, aarch64)
- clang 15.0.4, autotools

## 依赖
- libtirpc 1.3.7（TI-RPC，PR #6158 适配，待发布到制品仓）
  - autofs 需 clnttcp_create/clntudp_bufcreate 等（PORTMAP 兼容 API，libtirpc 产物已含）
  - autofs 不使用 DES（ecb_crypt/cbc_crypt），libtirpc 无需启用 AUTHDES
- pthread（OHOS SDK sysroot libc 缺线程取消 API，见下方 shim）

## 关键适配点

### 1. /proc 检测失败（HarmonyOS ostype）
- configure 的 AF_LINUX_PROCFS 检查 `/proc/sys/kernel/ostype` == "Linux"，
  OHOS 上返回 "HarmonyOS" → HAVE_LINUX_PROCFS 未定义 → automount.h #error
- 解决：conanfile.build() 中 Python 修改 include/automount.h，
  `#ifndef HAVE_LINUX_PROCFS` → `#if !defined(HAVE_LINUX_PROCFS) && !defined(__OHOS__)`

### 2. HMDFS config.status 权限问题
- configure 生成 config.status 后用 `umask 077` 创建临时目录（./confXXXXXX），
  HMDFS 全权限拒绝 → "Permission denied: confXXX/subs1.awk"
- 解决：conanfile.build() 用 Python 把 configure 中 `umask 077` 改为 `umask 000`
  （不用 toybox sed -i，其行为不可靠）

### 3. pthread 线程取消 API 缺失（ohos_pthread_shim.c）
- autofs 大量使用 pthread_setcancelstate（136 处）/pthread_testcancel/pthread_cancel
- OHOS SDK sysroot 的 libc.so 未导出这些符号（系统 libc 有 weak 符号但 SDK 没有）
- 解决：新增 lib/ohos_pthread_shim.c（补丁 0004），实现基于 TLS 标志 + 全局注册表的
  延迟取消语义，编译进 libautofs.so，daemon/modules 统一复用

### 4. 链接顺序（automount）
- 原规则 `$(CC) ... $(OBJS) $(LDFLAGS) $(LIBS) $(AUTOFS_LIB_LINK)` 中 -lautofs 在
  -lpthread 之后，libautofs.so 的 pthread 引用无法解析
- 解决：conanfile.build() 把规则改为 `... $(OBJS) $(LDFLAGS) $(AUTOFS_LIB_LINK) $(LIBS) -pthread`

### 5. toybox patch 局限性
- OHOS 的 patch 命令对"修改现有文件"的 hunk 不可靠（静默假成功）
- 因此修改现有文件（automount.h/lib Makefile/daemon Makefile/configure）的适配
  全部放入 conanfile.build() 的 Python 逻辑；补丁只保留新增文件
  （0004 ohos_pthread_shim.c，创建文件可靠）

## 编译产物
- sbin/automount（守护进程）
- lib/libautofs.so（内部库，含 pthread shim）
- lib/autofs/*.so（16 个模块：lookup_*, parse_sun/amd, mount_*）
- man pages

## 上游测试
- 上游无任何测试用例（无 make check 目标）
- test_package 补全 6 项断言：automount 存在、libautofs dlopen、
  4 个代表模块 dlopen

## 后续
- libtirpc 发布到制品仓后，autofs conan 配方依赖切换为制品仓版本
  （当前 requirements 已声明 libtirpc/1.3.7，本地构建时用本地安装制品）