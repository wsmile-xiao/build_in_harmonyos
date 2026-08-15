# accel-config 4.1.9 适配笔记（路径 B 知识库扩展）

## 编译日期
2026-08-13

## 编译状态
built（未 upload；本轮仅到 commit 前，不 push/PR）

## 任务信息
- 平台库：accel-config（Issue #2119，知识库扩展，路径 B 已由用户判定）
- 上游：intel/idxd-config，tag accel-config-v4.1.9
- 语言/构建：C / Autotools（configure.ac + Makefile.am + autogen.sh）

## 三重身份
- 任务平台名称：accel-config
- 上游仓库：idxd-config（GitHub）
- 归档：archives/a/accel-config/4.1.9/

## 构建环境（构建期工具，不入 PR）
- automake/1.18 + libtool/2.5.4 从 ohpcd Conan remote 获取，部署到 $HOME/autotools
  （构建机缺 aclocal/libtoolize；不写系统目录）
- autoconf 2.72 / pkg-config 0.29.2 / make 4.4.1 / clang 15 (aarch64-unknown-linux-ohos)
- TMPDIR 必须指向 $HOME 可写目录（/tmp 只读，E002 陷阱）

## 依赖闭环
- json-c/0.17：ohpcd 有 recipe（revision 3c6e9ba2），main 有归档，本机已有二进制缓存 ✅
- uuid/2.40.1（util-linux libuuid 拆分，包名 uuid 而非 libuuid）：ohpcd 有 recipe
  （revision e05bc8e1），main 有归档，本机从源码构建成功 ✅
- 自建 .pc 指向 Conan 包真实 include/lib（uuid 的 Cflags 应为 -I${includedir}，
  若写 -I${includedir}/uuid 会导致 <uuid/uuid.h> 解析为 .../uuid/uuid/uuid.h）

## 编译链路问题与修复（首个错误链）
1. `sh: aclocal: inaccessible or not found`（automake 缺失）→ conan 装 automake/1.18
2. `autom4te: Error in tempfile() ... Read-only file system`（/tmp 只读）→ TMPDIR=$HOME/tmp
3. `libtoolize: error: $pkgauxdir is not a directory: '//share/libtool/build-aux'`
   （conan 相对路径前缀）→ 设 `_lt_pkgdatadir=$HOME/autotools/libtool-2.5.4/share/libtool-conan`
4. `configure.ac:40: error: possibly undefined macro: AC_DEFINE`
   （误导性：实际是 PKG_CHECK_MODULES 的 pkg.m4 未被 aclocal 收录）→
   ACLOCAL_PATH 追加 /data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal
5. `configure: error: cannot guess build type`（config.guess 不认识 HarmonyOS，E007 同族）
   → 方案：不使用 --host=*-ohos 猜测，改用显式 --build/--host=aarch64-unknown-linux-gnu
   （与 uuid/2.40.1 配方一致；config.guess/sub 由 autogen 生成、不在 tarball 内，
   不能作为 conandata patches，故不打包 config.guess/sub 补丁）
6. `config.status: error: could not setup config files machinery`
   （mktemp 相对模板 `./confXXXXXX` 在受限 FS 上 Permission denied）→
   build-only mktemp wrapper（build_folder 临时 shim，mkdir 语义模拟
   `mktemp -d`，PATH prepend 仅作用于 configure/autogen 子进程；不修改生成
   configure，符合 R6）
7. `'uuid/uuid.h' file not found` → 修正 uuid.pc 的 Cflags
8. git-version 是 #!/bin/bash 而本机无 /bin/bash → 0003 补丁改 POSIX sh
9. PR #5266 CI（conan-build-test）失败根因：本机未声明的构建工具依赖
   （aclocal/automake/libtoolize 不在 CI PATH，gcc 不存在）→
   build_requirements() 声明 tool_requires automake/1.18 + libtool/2.5.4
   （仅 build context；autoconf/m4 由 SDK /data/service/hnp/bin 提供，不声明
   autoconf/2.72 以避免引入 OHOS perl/5.42.2 与 SDK perl 5.42.0 的
   XS 符号冲突）；移除 $HOME/autotools 硬编码；
   autogen 用 `bash -e` 让 autoreconf 失败立即传播；0004 补丁改
   autogen.sh libdir() 的硬编码 gcc 为 `${CC:-gcc}`。curl 缺失仅是 CI 预下载
   降级警告，不是包失败原因。

## 可移植性边界（路径 B 核心）
- 可移植（纯用户态）：JSON 配置解析（config.c/config_attr.c）、util/ 工具层、
  accfg_new/accfg_get_log_priority/accfg_unref 等只读 API
- Linux 专有（可编译、无设备不可验证）：/sys/bus/*/devices 枚举、sysfs 属性读写、
  /sys/bus/dsa/drivers/idxd/bind-unbind、/sys/module/idxd、/dev/dsa 字符设备路径、
  IDXD_SCMD_* ioctl 状态码（accfg/idxd.h）
- 硬件强依赖（不可移植）：dsa_test/iaa_test/libaccfg 测试 include immintrin.h 等
  x86 专有头，arm64 直接编译失败；runner 脚本需要真实 DSA/IAA + pasid_enabled=1 +
  kernel>=5.6，dsa_config_test_runner 会写真实设备配置

## 测试分层
- A 层上游：4 个 TESTS 入口 + test_all.sh 16 用例 → 全部 hardware-unrunnable
  （本机无 /sys/bus/dsa、/dev/dsa；EXIT_SKIP=77 条件真实存在但无法触发，
  未伪造 passed）
- B 层 test_package：pkg-config 消费 libaccel-config + uuid；编译链接消费者程序；
  调用只读 API（accfg_new/get_log_priority/set_log_priority/unref）；真实 self.run()
- C 层 mock sysfs：补丁注入 ACCFG_SYSFS_ROOT（默认 /sys，不改变生产语义）；
  仓库外 mock 树验证枚举 dsa0（devices_found=1）、空树返回 []、
  无 module 报 "idxd kernel module not loaded"；严禁模拟 bind/unbind 成功与真实 DMA

## 知识草稿
- knowledge/drafts/DRAFT-accel-config-sysfs-mock.kv / .md（draft=true，不 promote）
- 主题：Linux 硬件加速器配置库在 OpenHarmony 上的用户态可移植边界，
  以及通过 mock sysfs/无设备模式进行安全验证的方法
- 查重：knowledge/ 无 accel-config/idxd-config/Intel DSA/IAA 条目；
  与 E002/E007/E046/E051/E258 为不同主题

## 安全边界（已遵守）
- 未使用 sudo/su；未写 /sys、/dev/dsa、/sys/bus/dsa；未加载/卸载 idxd；
  未绑定/启用/禁用/配置真实设备与 WQ；未运行 dsa_config_test_runner/test_all.sh；
  未伪造硬件、未删断言、未把未运行测试写成 passed
---

**编译结束**: 2026-08-14 10:41
**最终状态**: built
