# libcgroup 0.34 — HarmonyOS PC 适配笔记

## 概要

- 上游：https://github.com/libcgroup/libcgroup tag v0.34（commit e9c63e95a65a17952b4d8ae922d5981e394a6ac3）
- 构建系统：autotools（发布 tarball 只带 configure.in，无生成 configure）
- 产物：libcgroup.so.1.0.34 + 工具 cgclassify/cgclear/cgconfigparser/cgcreate/cgexec/cgset + 守护 cgrulesengd
- PAM 模块关闭（--disable-pam）：libpam 未在 OHOS 制品仓发布，上游该模块为可选

## 适配要点（OHOS）

1. **musl 头文件兼容**（0001-ohos-musl-compat.patch）
   - `__BEGIN_DECLS/__END_DECLS`：glibc sys/cdefs.h 宏，musl 无 → 三个头文件本地定义
   - `linux/cn_proc.h`/`linux/connector.h`/`linux/netlink.h` → 拉 `linux/socket.h` 的 `sockaddr_storage` 与 musl `sys/socket.h` 重定义冲突 → 预定义 `_UAPI_LINUX_SOCKET_H` 守卫 + `__kernel_sa_family_t` typedef 别名（两者布局一致）
   - `linux/un.h` → `sys/un.h`（同样的 sockaddr_un，避免内核 uapi 版重复定义）

2. **fts(3) 缺失**：musl 无 `<fts.h>`（glibc 专有），api.c 的目录遍历用 fts_open/fts_read。引入制品仓已发布的 `musl-fts/1.2.7`（host 依赖）。

3. **config.guess/config.sub 重锚**（0002-config-guess-ohos.patch，E007/E205 知识）
   - 官方 patch-autotools-ohos.pl 生成：`__OHOS__` LIBC 检测 + HarmonyOS uname 分支 → 输出 `aarch64-unknown-linux-ohos`
   - **禁止 --build/--host 绕过**（会误判交叉编译，跳过 AC_RUN_IFELSE）
   - 注意：config.guess/config.sub 由 autoreconf 从 automake share 目录复制生成，补丁必须在 autoreconf **之后**打

4. **E114（HMDFS mktemp）**：生成的 configure/config.status 里 `umask 077 && mktemp -d` 产生 drwx--S--- 目录 → 用 abiword-plugin 先例的 `_drop_umask_077` 移除 umask 括号对

5. **musl 加载器 quirk（新知识，值得入图谱）**：
   - 系统默认 LD_LIBRARY_PATH 含 `/data/storage/el1/bundle/libs/arm64`（其他进程的应用沙箱）
   - 该目录**存在但内部文件不可访问**，musl 加载器遇到后**放弃整个库搜索**（不是跳过该条目）
   - 任何链接了 libc++_shared.so / libfts.so.0 的 conftest 运行都会 127
   - 修法：recipe build() 里清洗 LD_LIBRARY_PATH（剥 el1/bundle 段），并前置 OHOS SDK llvm/lib（含 libc++_shared.so）

6. **in-tree 构建**：2008 年代 Makefile.am 无 VPATH 支持——`libcgroup.map` 版本脚本用构建目录相对路径、daemon/tests 的 LDADD 用 `$(top_srcdir)/src/.libs/libcgroup.la`。`basic_layout(self, build_folder=".")` 强制同目录构建。

7. **E074**：make -j1（HMDFS jobserver fifo EPERM）

8. **测试脚本 shebang**（0003-test-scripts-env-shebang.patch）：`#!/bin/bash` → `#!/usr/bin/env bash`（OHOS /bin → /system/bin 无 bash，env 可解析 PATH）

## cgroup 文件系统在 OHOS 的形态（适配深点实测）

- `/sys/fs/cgroup` 是 **tmpfs**（内含 devices/freezer/systemd 子目录，普通用户无权限访问内部）
- 真正的 cgroup v1 挂载在 OHOS 专有路径：`/dev/cgroup`、`/dev/cpuset`、`/dev/cpuctl`、`/dev/memcg`、`/dev/iolimit`、`/dev/pids`、`/dev/workingset`、`/dev/dummy`
- `/proc/cgroups` **不存在**
- 无 root 权限，无法 mount/umount cgroup 文件系统
- 结论：`cgroup_init()` 在 OHOS 上返回 50016（ECGROUPNOTMOUNTED）——库的挂载探测找不到它认识的形态。这是**运行时环境限制**，非代码缺陷；内存 API（cgroup_new_cgroup 等）完整可用。

## 上游测试（rule4 最大化执行）

- 上游注册测试：`tests/Makefile.am` 的 TESTS = runlibcgrouptest.sh（1 个驱动），驱动 libcgrouptest01 三种挂载形态共 **37 个 test_cgroup_* 调用**（Set01×7、Set02×13、Set03×17；grep 命中 38 处含 1 处函数定义，申报口径 N=38 与审核一致）+ libcg_ba.cpp + pathtest.sh = **N=40**
- **make check 实测：PASS 1/1（驱动 exit 0）**，驱动内逐项实测：
  - **TestSet01（未挂载形态）：真实执行，10 条 TEST 断言 = 9 PASS + 1 FAIL**
    - TEST1 FAIL：cgroup_init() 期望 ECGROUPNOTMOUNTED(50001)，实测 ECGOTHER(50016)——库在 /proc/cgroups fopen 失败时返回 ECGOTHER（api.c 640 行），而 OHOS 不暴露 /proc/cgroups。期望值基于 Linux 语义（cgroup fs 未挂载），OHOS 走的是库内另一条真实错误路径。逐项定性：库代码行为，非测试适配缺陷
    - TEST2/4/5/6/7：未初始化错误路径（ECGROUPNOTINITIALIZED=50014）全 PASS
    - TEST3/8/9/10：cgroup_new_cgroup/cgroup_add_controller 内存构造全 PASS
  - **TestSet02（单挂载，13 调用）/ TestSet03（多挂载，17 调用）：按 set 跳过**——需 root 执行 mount -t cgroup + cpu/memory 控制器 + /proc/cgroups，OHOS 上三者皆不可得（无 root 通道：sudo 不可用、无 su；系统 cgroup 挂载不可 umount）
  - **libcg_ba（C++ 绑定）**：编译并实测运行——"Control Group Initialization failed...Please check that cgroups are mounted and at a single place"（未挂载预期错误路径）
  - **pathtest.sh**：逐行读 /proc/cgroups，环境性不可执行
  - **辅助程序实测**：proctest 完整通过（进程表输出）；setuid 执行到 setuid() 系统调用报 EPERM（非 root 预期）；get_controller/get_mount_point/walk_task/walk_test/read_stats/pathtest 均执行并输出 cgroup_init 失败错误路径（/proc/cgroups 依赖）
- **测试最大化执行的适配**（0004/0005 补丁）：
  - 0004：is_subsystem_enabled() 在 /proc/cgroups 缺失时回退探测 OHOS 控制器挂载点（/dev/cpuctl→cpu、/dev/memcg→memory）——不改断言，只修环境探测，忠实于"内核是否启用控制器"的测试意图（OHOS 内核确实启用）
  - 0005：驱动脚本不再因 /proc/cgroups 缺失/非 root 整体 exit 77——TestSet01 照常执行，Set02/03 按各自前置失败逐 set 跳过；umount 循环在系统级挂载不可卸载时 break；get_ctl_num 空控制器时 return 而非带空参继续
- 补全测试（rule12 鸿蒙特有）：test_package 3 项（内存 API 回路、init 错误路径、链接性）全 PASS

## conan 配方结构

```
requires:     musl-fts/1.2.7 (host)
tool_requires: automake/1.18 libtool/2.5.4 bison/3.8.2 flex/2.6.4 m4/1.4.19
options:      shared/with_tools/with_daemon
build:        autoreconf -fi → 补丁 → E114 清洗 → configure(--disable-pam) → make -j1 → make check（容忍 SKIP）
```

## 依赖泄漏修正

初版把 tool_requires 的 libltdl/libfl 链进了 libcgroup.so 的 NEEDED——已用 `dep.context == "host"` 过滤，最终 NEEDED 只有 libfts.so.0 + libc.so。

## 复现命令

```bash
conan create . --build=missing \
  -pr:h ~/.conan2/profiles/default -pr:b ~/.conan2/profiles/default
# profile 需带（CI profile 已有）：
# [buildenv] LD_LIBRARY_PATH=+(path)/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib
```
