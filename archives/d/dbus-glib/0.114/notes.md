# dbus-glib 0.114 适配笔记

## 编译环境
- 构建系统: autotools（发布 tarball 自带 configure）
- 编译日期: 2026-08-28
- 编译器: clang 15.0.4（/data/service/hnp/bin），三元组 aarch64-unknown-linux-ohos
- 依赖: dbus/1.14.10、glib/2.88.0（传递 expat/2.8.2、pcre2/10.45、zlib/1.3.1；glib 已 vendored libffi/gettext）
- 状态: built（探索编译完成；配方阶段见 HANDOFF）

## 编译步骤

在设备端用 conan 拉取依赖并生成 pkg-config（`conan install --requires=glib/2.88.0 --requires=dbus/1.14.10 -pr=h -pr=b=ci/conan/profiles/ohos-aarch64 -g PkgConfigDeps -g VirtualBuildEnv -g VirtualRunEnv`），然后：

1. `build-aux/config.guess`/`config.sub` 应用 E007 标准方案（`scripts/patch-autotools-ohos.pl`），并手工在 config.sub 内核-OS 白名单追加 `| linux-ohos*`。
2. `configure` 两处 `umask 077`→`umask 022`（HMDFS 私有目录内自写被拒，先例 libcsv/3.0.3 补丁 0002）。
3. **E236 la-free 方案**：把依赖 `.a` 复制到无 `.la` 的构建私有目录（`$HOME/tmp/builds/la-free`），显式传 `GLIB_LIBS/DBUS_LIBS="-L<la-free> -l…"`（pcre2 等包内 `.la` 的 `libdir='//lib'` 为过期路径，libtool 会顺死路径）。
4. 生成 `dbus-1.pc` 别名（dbus 包只出 `dbus.pc`，configure 需 `dbus-1`）；`AC_CHECK_LIB(expat)` 不吃 pkg-config，需注入 CPPFLAGS/LDFLAGS。
5. `./configure --prefix=$DEFAULT_PREFIX --enable-tests --disable-gtk-doc --disable-shared --enable-static && make`。

**必须 `--disable-shared`（本适配核心结论）**：glib/2.88.0 在本制品仓仅有静态二进制（registry 无 shared=True 预编译包，`conan install -o glib/*:shared=True` 实测 Missing prebuilt）。若构建共享库，`libdbus-glib-1.so` 会把 glib/gobject **整份吞入**成为私有副本；消费者（含上游测试）再链 `libgobject-2.0.a` 即形成**双 GType 运行时**：ref/unref 计数跨副本侥幸正确，但最后一次 unref 走 dispose 时在错误副本的类型表取 class vfunc → **PC=0 NULL 调用 SIGSEGV**（`test-specialized-types /ao/GSList` 稳定复现）。最小复现：同一 main.c 链 `.a` 通过、链 `.so` 崩溃。先例：`archives/a/avahi-glib/0.9_rc5`（`shared=False` 默认 + glib 缺 `.so` 时 raise）。修复后 ao 用例 6/6 全过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cannot find the library '//lib/libpcre2-8.la'` | E236：conan 依赖 `.la` 含过期 libdir | la-free 目录 + 显式 LIBS + 配方删除产物 `.la`（E236 主方案） |
| 2 | config.sub 不识别 `linux-ohos*` | E007 脚本白名单漏项 | config.sub:1779 手工加 `\| linux-ohos*` |
| 3 | configure mktemp/mkdir 私有目录自写被拒 | HMDFS umask 077 语义 | configure 两处 umask→022（libcsv 先例） |
| 4 | `test-specialized-types` ao/GSList SIGSEGV | 共享库吞 glib 静态副本→双 GType 运行时（PC=0） | `--disable-shared`（配方 `shared` 默认 False + glib 无 .so 守卫） |
| 5 | `run-peer-test.sh` bind `/tmp` EROFS | 鸿蒙 /tmp 只读 erofs（E002 同类） | peer-server.c 补丁：TMPDIR 感知 |
| 6 | TMPDIR 下 bind `Operation not permitted` | HMDFS 不支持 AF_UNIX 文件 socket（/dev/shm 亦 EACCES，实测矩阵） | peer-server.c 补丁升级为 abstract 命名空间优先、tmpdir 回退；P2P IPC 真实通过 |
| 7 | gdb/strace 无法调试崩溃 | SELinux/HMMAC 内核级封锁 ptrace（ptrace-alternatives §2） | 自写 SIGSEGV handler + FP 链回溯 + llvm-addr2line 符号化（方法可复用） |

## 源码修改（探索期，未生成 .patch；refresh-patch 基线 = dbus-glib-0.114.orig）

- `build-aux/config.guess`、`build-aux/config.sub`：E007 + linux-ohos 白名单
- `configure`：umask 022 ×2（保持与 configure.ac 一致性由 refresh-patch 验证）
- `test/core/peer-server.c`：listen 地址 abstract 优先（`unix:abstract=org.freedesktop.DBus-glib-test.<pid>`）→ `unix:tmpdir=$TMPDIR` 回退；仅测试工具，不触库本体
- `test/core/proxy-peer.c`：listen 地址 TMPDIR 感知（同文件的上游硬编码 `/tmp`）；该程序仅经 run-test.sh 调用，本机因无 dbus-run-session 未获运行时验证（构建通过）

## 依赖版本

dbus/1.14.10、glib/2.88.0、expat/2.8.2、pcre2/10.45、zlib/1.3.1（均 ohpcd 制品仓实测已发布）

## 验证结果

```bash
# 构建树：$HOME/tmp/builds/dbus-glib-0.114.work（静态最终配置）
make -j2 && echo ok                       # exit=0，日志 dbusglib-{configure2,make2,make-static}.log
make -k check                             # TOTAL 8 / PASS 5 / FAIL 3，日志 dbusglib-check-{static,final}.log
# PASS: dbus-glib-test, test-errors, test-compile-nested.sh, test-specialized-types, run-peer-test.sh
# FAIL（全部 exit 127，设备无会话总线工具，原始行）：
#   tests/test-30574      ../build-aux/test-driver[119]: dbus-run-session: inaccessible or not found
#   run-test.sh (core)    ./../../tools/run-with-tmp-session-bus.sh[50]: dbus-run-session: ... not found
#   run-test.sh (interfaces) 同上
# 设备总线能力矩阵（实测）：dbus-daemon/run-session/launch 不存在（PATH、/system/bin、hnp、conan dbus 包 bin/ 均无）；
#   AF_UNIX bind：/tmp=EROFS、$HOME/tmp(HMDFS)=EPERM、/dev/shm=EACCES、abstract 命名空间=OK
make install DESTDIR=$HOME/tmp/test-install-dbus-glib-0.114   # exit=0，staging 完整
# 安装后二进制实测：
dbus-binding-tool --version               # rc=0
dbus-binding-tool --mode=glib-client --output=... test/data/nested-introspect.xml  # rc=0，51 行 glue
# IPC 真实功能验证（无守护进程路径）：run-peer-test.sh rc=0
#   = dbus_g_connection_open(abstract) + DoNothing 往返 + Increment(42)==43 返回值断言 + Frobnicate 信号回调退出
```

未覆盖项：需要 session bus 的 marshalling/接口级测试（3 项，归因平台无 dbus-daemon，见上矩阵）；test-proxy-peer 运行时。

## 注意事项

- 配方（任务 #6）必做：`shared` 默认 False；OHOS 且 glib 无 `.so` 时若请求 shared → raise（avahi-glib 先例）；`--disable-gtk-doc`；dbus-1.pc 别名与 expat CPPFLAGS/LDFLAGS 注入（`AC_CHECK_LIB` 不吃 pkg-config）；E236 la-free 在 generate()/build() 重现且**删除包内 `.la`**；expat 只有 `.so`，test_package/conanrun 须带运行时路径；R38 需软件级 `commands.json`（bin_PROGRAMS=dbus-binding-tool）。
- 新知识候选（W5/R31，graph add --draft）：①静态库依赖被共享库吞入→双运行时 SIGSEGV（本例 glib；同类风险任何 static-only 依赖+shared 消费者）；②鸿蒙 AF_UNIX 文件 socket 全域不可 bind、abstract 可用；③无 ptrace 下 handler+FP 链+addr2line 崩溃定位方法。
- 禁止提交：本 notes 正常入 PR；HANDOFF 与 `.build-context-*`、`archives/l/libXext/` 伪改动不入任何提交。

## 对话索引（上下文裁剪协议）

### 对话 #2 — 2026-08-28 14:45
**操作**: 从 E236 make 卡点恢复；完成 make/check/install；定位 ao SIGSEGV=双 glib 运行时并改静态构建；peer 测试 abstract socket 适配
**结果**: ✅ 8 项测试 5 过（原 3 过），3 败全部归因设备无 session bus（exit 127 原始日志留档）
**知识图谱**: E236、E007、E249（SIGSEGV 所有权模式近似命中，实际根因为双副本）、E002（/tmp 只读同族）
**上下文状态**: 已裁剪（ASan/gdb/addr2line 调试过程不入上下文，保留本索引）
---

**编译结束**: 2026-08-28 16:45
**最终状态**: built
