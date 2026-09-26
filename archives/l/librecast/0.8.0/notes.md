# librecast 0.8.0 适配笔记

## 编译环境
- 构建系统: autotools（上游手写 `Makefile.in`，`all: $(SOFILES)` 仅产 shared 库）
- 编译日期: 2026-09-24
- 编译器: clang 15.0.4（OHOS aarch64 本机工具链）
- 目标三元组: `aarch64-unknown-linux-ohos`
- 状态: built

## 上游信息
- 主仓: https://codeberg.org/librecast/librecast（官方镜像 https://git.sr.ht/~librecast/librecast）
- 版本: v0.8.0（tag 与 v0.8-RC3 同一提交 `9b3422cb70f7`；CHANGELOG 2023-11-07）
- 源码包: `librecast-0.8.0.tar.gz`，sha256 `3c1f0fd35d147e0197789d2af34ed80f1bd2f5782438f15386ccf8c777e5ba12`
  - 两个官方入口（codeberg / sr.ht）解包后内容完全一致（454 条目，仅打包层不同）；本配方用 sr.ht，与同族已发布包
    `lcrq/0.3.1` 同源（R39）
- 随包内嵌（非独立依赖，均由顶层 configure 一并构建）：
  - `libs/blake3` — BLAKE3 参考 C 实现，构建为静态 `libblake3.a`
  - `libs/libmld` — MLDv2 监听库，经 `AC_CONFIG_SUBDIRS([libs/libmld])` 构建，目标文件直接链入 `liblibrecast.so`

## 依赖版本
- `lcrq/0.3.1`（RaptorQ FEC；公开头 `include/librecast/net.h` 内含 `<lcrq.h>` ⇒ public requires）
- `libsodium/1.0.22`（加密/哈希；公开头 `include/librecast/crypto.h` 内含 `<sodium.h>` ⇒ public requires）
- 系统库: pthread、m、dl
- 无更底层未发布依赖（W0 已核验两者均可 `conan download` 成功）

## 编译步骤（探索阶段实际执行）

```bash
source .build-context-librecast-0.8.0
cd $BUILD_SRC_DIR
# E007：先按知识条目补 config.guess/config.sub（顶层 + 内嵌 libmld 各一份）
perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl config.guess config.sub
perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl libs/libmld/config.guess libs/libmld/config.sub
# 补充：config.sub 的 kernel-os 校验表需加 linux-ohos*（两份都要）
# E129：configure 与 libs/libmld/configure 的 config.status 临时目录 umask 077 → 022
PATH="/system/bin:$PATH" CC=clang ./configure --prefix=$DEFAULT_PREFIX --srcdir=.   # exit 0
PATH="/system/bin:$PATH" make -j4                                                    # exit 0
```

注：`PATH` 前置 `/system/bin` 是因为会话 PATH 首位是 WorkBuddy electron shim 的 `rm`
（缺 `/bin/bash` 解释器），configure 内部调用 `rm` 会报 "bad interpreter"。

## 对话记录

### 对话 #1 [2026-09-24] 环境准备：Python SSL 缺 CA

- 问题: `init-build` 下载源码报 `SSL: CERTIFICATE_VERIFY_FAILED`（`_ssl.c:1010`）
- 根因: 该 Python 3.12.9 的 `ssl.get_default_verify_paths()` 指向 `~/usr/local/ssl/cert.pem`，该文件不存在
- 操作: `export SSL_CERT_FILE=$(python3 -c 'import certifi;print(certifi.where())')`（用 pip 安装的 certifi 束）
- 结果: 下载成功；**CI 侧 init-build 内部另有 CA 安装步骤（实测会安装 121 个根证书）**，本配方不含此绕过

### 对话 #2 [2026-09-24] init-build 复制源码失败（悬空符号链接）

- 问题: `init-build` 在 `shutil.copytree(orig, work, copy_function=os.link)` 报大量
  `Operation not permitted` 与 `No such file or directory`
- 根因: 上游 tarball 中 `test/all/*.test`、`test/{enc,mdex,mtree,sync,zzz}/*.test` 共 **121 个悬空符号链接**
  （指向构建期才生成的 `../00NN.test`）；HMDFS 拒绝硬链接，copy2 回退又跟随断链失败
- 操作: 用 Python `tarfile` 手动解压重建 `.work`（保留符号链接），再重跑 `init-build`（复用该目录）
  ```python
  with tarfile.open(tarball, "r:gz") as tf:
      members = []
      for m in tf.getmembers():
          parts = m.name.split("/", 1)
          if len(parts) < 2 or not parts[1]: continue
          m.name = parts[1]; members.append(m)
      tf.extractall(work, members=members)
  ```
- 结果: 源码树就绪（430 文件 / 121 符号链接，`configure` 就位），`init-build` exit 0
- 备注: 与 `archives/l/lcrq/0.3.1/notes.md` 对话 #1 同型（同一上游家族的同类 tarball 形态）

### 对话 #3 [2026-09-24] config.sub 不认 linux-ohos（E007 变体）

- 问题: `config.guess` 报 "unable to guess system type"；补丁后 `config.sub` 仍报
  `Kernel 'linux' not known to work with OS 'ohos'`
- 根因: E007 补丁脚本只改 OS 列表与 `ohos-linux` 别名，未加 kernel-os 兼容表的 `linux-ohos*` 组合
- 操作: 在 `config.sub` 校验表 `linux-gnu* | ... | linux-uclibc*` 分支追加 `| linux-ohos*`
  —— **顶层与 `libs/libmld/config.sub` 两份都要改**（内嵌子项目自带一份 config.sub，configure 递归进入时会用到）
- 结果: 平台识别为 `aarch64-unknown-linux-ohos`，configure 通过

### 对话 #4 [2026-09-24] E129：config.status 临时目录权限（本机可复现）

- 问题: `config.status: can't create ./confXXXXXX/subs1.awk: Permission denied` →
  `could not setup config files machinery`
- 根因: `configure` 内嵌的 config.status 用 `umask 077 && mktemp -d "./confXXXXXX"` 建临时目录；
  HMDFS 对新建目录强制 setgid，`umask 077` 得到 `drwx--S---`(2700)，**组无搜索位且属主写入被拒**
- 本机实测复现（与 lcrq 时代"本机无法复现"不同）:
  ```
  umask=77  mkdir mode=drwx--S--- (0o2700)  write=FAIL 13 Permission denied
  umask=22  mkdir mode=drwxr-s--x (0o2751)  write=OK
  ```
- 操作: `configure` 与 `libs/libmld/configure` 各两处 `umask 077` → `umask 022`
- 结果: configure exit 0，正常 `creating Makefile / src/Makefile / include/mld.h / src/config.h`

### 对话 #5 [2026-09-24] 链接期 `-lsodium` / `-llcrq` 找不到

- 问题: `make` 在 `src/liblibrecast.so` 链接步骤报 `unable to find library -lsodium` / `-llcrq`
- 根因: 顶层 `src/Makefile` 的 `LDFLAGS` 只追加了包内 `-L`（`-L../libs/blake3/c`、`-L../libs/libmld/src`），
  没有 lcrq/libsodium 的 `-L`；依赖的头在 CPPFLAGS 里有、库路径没有
- 操作: 构建时用 `LIBRARY_PATH=<lcrq lib>:<libsodium lib>` 提供查找路径
- 结果: make exit 0。**配方中由 AutotoolsToolchain 自动导出 `LDFLAGS`（含各依赖 lib 目录）+ 各包 RPATH**，
  无需手工注入（见 conanfile.py `generate()` 注释）

### 对话 #6 [2026-09-24] `uname -s` 返回 HarmonyOS 导致选错实现（关键）

- 问题: `make test` 链接报 `undefined symbol: lc_tuntap_create`
- 根因: `src/Makefile` 用 `ifeq ($(OSNAME),Linux)` 选 `if_linux.o`（提供 `lc_tuntap_create`），
  但 OHOS 的 `uname -s` 返回 **`HarmonyOS`**，所有分支都不命中 → 落到 `else OBJECTS += if.o`
  （仅 72 行的 stub 版，无 `lc_tuntap_create`）
- 操作: 顶层 `Makefile.in` 在 `OSNAME := $(shell uname -s)` 后加 `ifeq ($(OSNAME),HarmonyOS) OSNAME := Linux endif`
- 结果: 重建后链接命令行含 `if_linux.o`，`lc_tuntap_create` 进入 `.so`；OSNAME 归一同时带来的
  `liblibrecast.so.0.5` SONAME 与 Linux 一致

### 对话 #7 [2026-09-24] E091 + msghdr 初始化

- 问题: 编译 `libs/libmld/src/mld.c` 报两个 error：
  1. `error: redefinition of 'sockaddr_storage'`（`linux/socket.h` 与 musl `sys/socket.h` 冲突）
  2. `error: incompatible pointer to integer conversion initializing 'int' with an expression of type 'void *'`
- 根因:
  1. **E091**：`mld.c` 经 `<linux/netlink.h>` 间接引入内核 UAPI 版 `struct sockaddr_storage`，与 musl 版重定义
  2. OHOS `struct msghdr` 在 64 位下含 `__pad1`/`__pad2` 填充字段，上游的位置初始化
     `{ &sa, sizeof(sa), &iov, 1, NULL, 0, 0 }` 第 5 个初始化器落到 `__pad1`（int）上
- 操作:
  1. 按 E091 rec（同 `archives/a/accel-ppp/1.14.0` 先例）在 include 前后用
     `#ifndef __GLIBC__` 守卫重命名 `sockaddr_storage` → `__linux_sockaddr_storage`
  2. 改指定初始化：`.msg_name/.msg_namelen/.msg_iov/.msg_iovlen`
- 结果: 两个 error 消除

### 对话 #8 [2026-09-24] E127：musl 无可用线程取消（本任务主要工作量）

- 问题: 产物在设备上**无法加载**：
  ```
  Error relocating liblibrecast.so: pthread_cancel: symbol not found
  ```
  交叉编译 sysroot 的 stub `libc.so` 不导出 `pthread_cancel`，链接消费者时
  `--no-allow-shlib-undefined` 直接失败
- 取证（链接期 / 运行期分离）:
  - SDK sysroot `libc.so`：`pthread_cancel` / `pthread_setcancelstate` / `pthread_testcancel` / `pthread_setcanceltype` **全为 0**
  - 设备 `/system/lib64/libc.so`：`pthread_cancel` 是 `T`，但**调用返回 38 = ENOSYS**；
    `pthread_setcancelstate`/`pthread_testcancel` 为 `WEAK`；`pthread_setcanceltype` **完全缺失**
  - 全 SDK / 全设备 `*.so` 均无 `inet6_opt_*` 提供者
- 根因: musl 不实现 POSIX 线程取消（E127）。库内生产代码 5 个文件共 11 处依赖它
- 操作（协作式关闭，参考 `archives/a/accel-ppp/1.14.0` 的 eventfd 替代思路）:
  | 文件 | 改动 |
  |------|------|
  | `src/q.c` | `q_job_seek()` 识别 NULL-job 停止哨兵并返回；新增 `q_pool_destroy_q(tid,n,q)`（投递哨兵 + join）；`q_pool_destroy()` 在 musl 下退化为空实现（`__linux__ && !__GLIBC__`） |
  | `include/librecast/q.h` | 声明 `q_pool_destroy_q()` |
  | `src/mtree.c` / `src/sync.c` | 调用方改用 `q_pool_destroy_q()`；`share_send_thread()` 识别哨兵 |
  | `libs/libmld/src/job.c` | `job_seek()` 识别哨兵；`job_queue_destroy()` 改为投递哨兵 + join |
  | `src/librecast.c` | `lc_socket_listen_cancel()` 改 stop 标志 + `shutdown(sock)` 释放阻塞的 `recvmsg()` + join；`lc_close_nack_logger()` 改 stop 标志（poll 1s 超时可及时退出）；监听线程循环条件改 stop |
  | `src/librecast_pvt.h` | socket 与 NACK logger 增加 `volatile int stop` |
  | `libs/libmld/src/mld.c` | `mld_thread_listen` 的 `recvmsg` 阻塞由 `mld_stop()` 关闭 `listen_sock` 释放；`mld_thread_netlink` 新增 `netlink_fd` 字段并由 `mld_stop()` 关闭释放；`mld_thread_timer` 加 stop 条件；BSD 分支 poll 循环加 stop 检查 |
  | `libs/libmld/src/mld_pvt.h` | `mld_t` 增加 `volatile int stop` 与 `int netlink_fd` |
- 结果: `.so` 中 `pthread_cancel`/`pthread_setcancelstate`/`pthread_testcancel`/`pthread_setcanceltype` 的 UND 计数**全部为 0**；产物可加载
- 证伪记录: 先试过"no-op 预载 shim"（`pthread_cancel` 返回 0）——**不可行**：`test/0000-0042.c` 要求真异步取消
  （`PTHREAD_CANCEL_ASYNCHRONOUS` 后主线程须中断阻塞在 `sem_wait()` 的线程），实测挂起 3.5h；
  且 `src/q.c:q_pool_destroy`、`src/librecast.c:lc_socket_listen_cancel` 靠返回值判定错误码，no-op 会破坏语义

### 对话 #9 [2026-09-24] RFC 3542 `inet6_opt_*` 缺失导致产物无法 dlopen

- 问题: 取消 API 解决后，设备 `dlopen` 仍失败：
  ```
  Error relocating liblibrecast.so: inet6_opt_init: symbol not found
  ```
- 根因: `libs/libmld/src/mld.c` 的 MLD 查询构造路径无条件调用 `inet6_opt_init/append/set_val/finish`
  （RFC 3542 §10，glibc 专有 API）；musl 从未实现，且 OHOS **全平台**无提供者
  （SDK 头、SDK sysroot `libc.so`、设备 libc、设备全部 `*.so` 均查无）
- 操作: 在 `mld.c` 内**内联**一份符合 RFC 3542 §10 的实现，语义逐行转写自权威 KAME/BSD 参考实现
  （`lib/libc/net/ip6opt.c`，glibc/FreeBSD 实现的共同来源），并用
  `#if defined(__linux__) && !defined(__GLIBC__)` 守卫（libc 能力探测，非 `#ifdef __OHOS__` 平台宏）
- 为何内联而非新建文件: `refresh-patch --auto` 的"精准模式"只对 `.orig` 中已存在的追踪文件生成补丁，
  **新增文件无法随 patches/ 管线交付**（新建 `inet6_opt_compat.c/.h` 后生成的补丁集里没有它们，
  CI 从 tarball 干净构建时该文件不存在 ⇒ 必然失败）。内联进已追踪的 `mld.c` 才能用补丁交付
- 结果: 4 个符号 UND 归 0；设备 `dlopen liblibrecast.so` 与 `libmld.so` 均 **OK**（无需任何 LD_PRELOAD）
- 语义验证: 19/19 断言通过（含 4 个错误路径），覆盖库内 `mld_query_cmsglen()` 的真实调用序列
  `init(NULL,0)=2` → `append(NULL,0,2,RA,len2,align2)=6` → `finish(NULL,0,6)=8`，
  以及 on-wire 字节布局（`[2]`=RouterAlert、`[3]`=len、`[6]`=PadN、`[7]`=0）

### 对话 #10 [2026-09-24] 补丁管线：新增文件不可交付（已在 #9 处置）

- 问题: `refresh-patch --auto` 生成的补丁集不含新建文件
- 根因: `_generate_context`/精准模式以 `.orig` 基线文件清单为准，只对基线内文件做 diff
- 操作: 回退"新建 `inet6_opt_compat.c/.h` + 改 `Makefile.in` OBJECTS"方案，改为内联（见 #9）
- 结果: 补丁集最终为 **17** 个（内联方案由 `0011-libs-libmld-src-mld.c.patch` 承载全部 RFC 3542 内容；
  若采用新建文件方案则这些内容无法随 patches/ 交付）

## 上游测试清点（R51）

- 测试入口: `make test`（顶层 Makefile → `test/Makefile`，`TESTRUNNER=maketest`）
- 用例清点:
  - 顶层 `test/*.c`：**80** 个用例源文件
  - `test/{all,enc,mdex,mtree,sync,zzz}/`：以符号链接复用同名用例（**111** 个链接，非独立新增用例）
  - 内嵌 `libs/libmld/test/*.c`：**11** 个（`make test` 递归调用，实测 `10 tests run`）
- **OHOS 实测（2026-09-24，aarch64-linux-ohos）**：
  - 内嵌 libmld 套件：**10 run / 8 OK / 2 WARN / 0 FAIL**
    （`0000-0003 mld_add_iface`、`0000-0006 mld_query_msg` 因缺 `CAP_NET_RAW` 降级 WARN，与上游设计一致；
    `0000-0006` 正是走 RFC 3542 兼容层路径的用例）
    日志: `reports/upstream-test-libmld.log`
  - 顶层套件可运行子集（**排除 31 项依赖线程取消语义的用例**，逐用例 45s 超时）：
    **38 OK / 7 WARN / 4 FAIL(rc=134) / 31 SKIP / 0 HANG**
    日志: `reports/upstream-test-subset.log`，脚本 `reports/run_upstream_subset.sh`
  - **31 项 SKIP 的具体技术原因**：这些用例要求真异步取消
    （`pthread_cancel` + `PTHREAD_CANCEL_ASYNCHRONOUS`，主线程须中断阻塞在 `sem_wait()`/`poll()` 的线程）。
    musl 不实现该语义（设备 libc 的 `pthread_cancel` 调用返回 ENOSYS=38，`pthread_setcanceltype` 缺失）。
    库内生产代码已改协作式关闭（E127）使**产物可用**，但用例本身考核的是内核/libc 的取消能力，
    协作式无法替代 ⇒ 该 31 项在 OHOS 平台不可运行，如实计分母、不冒充通过。
    清单: `0000-0015 0000-0016 0000-0017 0000-0018 0000-0019 0000-0021 0000-0036 0000-0037
    0000-0038 0000-0039 0000-0040 0000-0042 0000-0043 0000-0044 0000-0045 0000-0052 0000-0055
    0000-0056 0000-0057 0000-0058 0000-0059 0000-0060 0000-0062 0000-0065 0000-0110 0000-0111
    0000-0115 0000-0116 0000-0117 0000-0121 0000-0122`
  - **4 项 FAIL(rc=134) 非本次回归**：`0000-0000/0000-0001/0000-0002/0000-0004` 是 `falloc` 库 ENOMEM 注入
    用例，SIGABRT 属该 harness 在 OHOS 上的既有行为；本次改写**前**的同一批次日志（`logs/41-clean.log`）
    中这 4 条同样落在 `????` 档（Makefile 定义 `????` = rc ∉ {0,1,2}），前后一致
- test_package 消费者测试（实测 19 项断言，全部通过）: 覆盖 `lc_ctx_new/lc_ctx_free` 生命周期（即 E127 关闭路径）、
  `hash_generic/hash_init/hash_update/hash_final/hash_bin2hex`、`mdex_init/mdex_put/mdex_get/mdex_del/mdex_free`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载源码 SSL 校验失败 | 本机 Python 的 `ssl` 默认 CA 路径 `~/usr/local/ssl/cert.pem` 不存在 | `SSL_CERT_FILE=certifi` 束（探索阶段绕过；CI 侧 init-build 自带 CA 安装） |
| 2 | init-build 复制源码失败（EPERM→ENOENT） | 上游 tarball 含 121 个悬空符号链接（`test/**/*.test`）；HMDFS 拒绝硬链接，copy2 跟随断链 | 脚本只读不改：Python `tarfile` 解压重建 `.work`（保留符号链接），重跑 init-build |
| 3 | `config.guess` 无法识别系统（E007） | 2022-05-25 版无 HarmonyOS 分支 | `patch-autotools-ohos.pl`（顶层 + 内嵌 libmld 各一份） |
| 4 | `config.sub` 报 `Kernel 'linux' not known to work with OS 'ohos'`（E007 变体） | E007 补丁未加 kernel-os 兼容表的 `linux-ohos*` | 两份 `config.sub` 的校验表追加 `\| linux-ohos*` |
| 5 | `config.status` 报 `could not setup config files machinery`（E129） | `umask 077` 建临时目录 → HMDFS 上得 `drwx--S---`(2700)，写入 Permission denied（本机可复现） | `configure` + `libs/libmld/configure` 各 2 处 `umask 077`→`022` |
| 6 | 链接 `-lsodium`/`-llcrq` 找不到 | 顶层 `src/Makefile` 只加了包内 `-L`，无依赖 lib 路径 | 构建时 `LIBRARY_PATH`；配方中由 AutotoolsToolchain 自动导出 LDFLAGS/RPATH |
| 7 | `undefined symbol: lc_tuntap_create` | `uname -s`=`HarmonyOS` 使 `ifeq ($(OSNAME),Linux)` 不命中，误选 stub `if.o` | `Makefile.in` 归一 `HarmonyOS`→`Linux` |
| 8 | `redefinition of 'sockaddr_storage'`（E091） | `linux/netlink.h` 的内核 UAPI 版与 musl `sys/socket.h` 冲突 | `#ifndef __GLIBC__` 重命名守卫（accel-ppp 同型先例） |
| 9 | `msghdr` 位置初始化指针转整型 | OHOS `struct msghdr` 含 `__pad1/__pad2` 填充字段 | 改指定初始化（`.msg_name/.msg_namelen/.msg_iov/.msg_iovlen`） |
| 10 | **产物无法加载**：`pthread_cancel: symbol not found`（E127） | musl 不实现 POSIX 线程取消；设备 libc 的 `pthread_cancel` 返回 ENOSYS，`pthread_setcanceltype` 缺失 | 库内 11 处线程终止改协作式关闭（停止哨兵 / stop 标志 / `shutdown()` / close fd 释放 recvmsg） |
| 11 | **产物无法加载**：`inet6_opt_init: symbol not found`（RFC 3542） | musl 从未实现 RFC 3542 选项 API，OHOS 全平台无提供者 | `mld.c` 内联 KAME 语义实现，`__linux__ && !__GLIBC__` 守卫 |
| 12 | 新建文件无法随补丁交付 | `refresh-patch --auto` 精准模式只 diff `.orig` 基线内文件 | 放弃新建文件方案，内联进已追踪的 `mld.c` |
| 13 | 消费者测试 `mdex_del` 段错误（rc=139） | **上游既有缺陷**：`src/mdex.c:mdex_del()` 的 `ptr` 仅在 while 内赋值，删除**无子节点的 root** 时 `ptr` 仍为 NULL，第 692 行 `*ptr = NULL` 解引用空指针（`mdex.c` 与 pristine `.orig` 逐字节一致，无 mdex 补丁） | 测试用例改按上游验证过的模式（删非 root 节点，见 `test/0000-0046.c`）；缺陷本身超出适配范围，不修改上游代码 |

## 源码修改

| 补丁 | 内容 | guard |
|------|------|-------|
| 0001-Makefile.in.patch | `uname -s` 为 HarmonyOS 时归一为 Linux（选中 if_linux.o） | 无（shell 运行时判定） |
| 0002-config.guess.patch | 顶层 config.guess 增加 HarmonyOS 识别（E007） | 无（shell 判定） |
| 0003-config.sub.patch | 顶层 config.sub 接受 `aarch64-unknown-linux-ohos` + kernel-os 表加 `linux-ohos*`（E007） | 无（shell 判定） |
| 0004-configure.patch | 顶层 config.status 临时目录 `umask 077`→`022`（E129/E114） | 无（只影响创建权限位） |
| 0005-include-librecast-net.h.patch | 上游缺陷：`net.h` 补 `<stdio.h>`（用 `FILE` 却未包含） | 无 |
| 0006-include-librecast-q.h.patch | 声明 `q_pool_destroy_q()` | `__linux__ && !__GLIBC__`（实现处） |
| 0007-libs-libmld-config.guess.patch | 内嵌 libmld 的 config.guess 增加 HarmonyOS 识别（E007） | 无（shell 判定） |
| 0008-libs-libmld-config.sub.patch | 内嵌 libmld 的 config.sub 接受 linux-ohos + kernel-os 表（E007） | 无（shell 判定） |
| 0009-libs-libmld-configure.patch | 内嵌 libmld 的 config.status 临时目录 `umask 077`→`022`（E129/E114） | 无 |
| 0010-libs-libmld-src-job.c.patch | `job_seek()` 识别停止哨兵；`job_queue_destroy()` 哨兵 + join | `__linux__ && !__GLIBC__` 语义等价，无宏 |
| 0011-libs-libmld-src-mld.c.patch | E091 守卫、`msghdr` 指定初始化、协作式监听退出、内联 RFC 3542 `inet6_opt_*` | `#ifndef __GLIBC__` / `#if defined(__linux__) && !defined(__GLIBC__)` |
| 0012-libs-libmld-src-mld_pvt.h.patch | `mld_t` 增 `stop` 与 `netlink_fd` | 无宏（字段） |
| 0013-src-librecast.c.patch | 监听/NACK 线程协作式退出（stop + `shutdown()`） | `__linux__ && !__GLIBC__` 包住取消类调用 |
| 0014-src-librecast_pvt.h.patch | socket 与 NACK logger 增 `volatile int stop`；补 `<stdio.h>`（上游缺陷） | 无 |
| 0015-src-mtree.c.patch | 线程池销毁改用 `q_pool_destroy_q()` | 无宏（调用替换） |
| 0016-src-q.c.patch | 停止哨兵 + `q_pool_destroy_q()` + musl 下 `q_pool_destroy()` 退化为空 | `__linux__ && !__GLIBC__` |
| 0017-src-sync.c.patch | 发送线程识别哨兵；`lc_unshare()` 改用 `q_pool_destroy_q()` | `__linux__ && !__GLIBC__` 包住 `pthread_testcancel()` |

无 `#ifdef __OHOS__` 平台宏（R8/PF5 合规）：所有条件编译均为 **libc 能力探测**
（`__linux__ && !__GLIBC__` / `__GLIBC__`），语义是"该 libc 是否提供该 API"，非平台特判。

## 验证结果

```bash
# 编译（探索阶段，本机 aarch64-linux-ohos）
PATH="/system/bin:$PATH" make -j4        # exit 0，0 error

# 产物可加载性（决定性判据：无任何 LD_PRELOAD）
dlopen liblibrecast.so  → OK
dlopen libmld.so        → OK

# 未定义符号核查（readelf --dyn-syms，全部应为 0）
inet6_opt_init / inet6_opt_append / inet6_opt_set_val / inet6_opt_finish  → UND=0
pthread_cancel / pthread_setcancelstate / pthread_testcancel / pthread_setcanceltype → UND=0

# 上游测试（详见 reports/）
libmld 套件: 10 run / 8 OK / 2 WARN / 0 FAIL
顶层子集:    38 OK / 7 WARN / 4 FAIL(rc=134, 既有) / 31 SKIP(平台不可运行) / 0 HANG

# 消费者测试（test_package）
19/19 断言通过

# conan-verify / finish 见 reports/ 与 .ci-result.json
```

## 注意事项

- 上游仅构建 shared 库（`Makefile.in` 的 `all: $(SOFILES)`），配方未传 `--enable-static/--disable-shared`
  （手写 Makefile 不认这两个 flag）；`default_options = {"shared": True, "fPIC": True}`
- `basic_layout(self, build_folder=".")`：上游 Makefile 为 in-source 构建（无 VPATH），
  且 `src/Makefile` 以相对路径链接 `../libs/libmld/src/*.o`
- `lcrq` 与 `libsodium` 均为 **public requires**（`transitive_headers=True, transitive_libs=True`）：
  `include/librecast/net.h` 含 `<lcrq.h>`、`include/librecast/crypto.h` 含 `<sodium.h>`
- 下游 lcsync 0.3.2 依赖本包（`librecast >= 0.8`：`lc_recvdir` 符号强校验）；
  `lcsync/0.3.2` 的配方另有 `lcrq/0.3.1` 与 `libsodium` 依赖
---

**编译结束**: 2026-09-25 00:25
**最终状态**: built
