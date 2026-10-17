# termrec 0.19 适配笔记

## 编译环境
- 构建系统: autotools（上游 tag 不含生成的 configure/Makefile.in，需 autogen.sh 引导）
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4（OHOS SDK，target aarch64-unknown-linux-ohos）
- 编译状态: built

## 编译步骤
1. `source()`：GitHub tag v0.19 tarball（sha256 0550c122…），经共享 dlcache 命中
2. `generate()`：
   - `VirtualBuildEnv` + `AutotoolsDeps`（后者注入依赖的 CPPFLAGS/LDFLAGS/LIBS — configure.ac 用 AC_CHECK_LIB 探测压缩库）
   - `AutotoolsToolchain` 追加 `--build/--host=aarch64-unknown-linux-gnu`（config.guess 不识 HarmonyOS uname）
   - 环境：`CONFIG_SHELL` unset + `SHELL=/bin/sh`（§12.38① hnp bash 在 HMDFS 下 getcwd 必挂）
   - `LD_LIBRARY_PATH` 注入依赖 libdir 绝对路径（zstd 为 shared-only，zstd 系 conftest/工具运行时需要）
   - PATH 前置 mktemp wrapper（build-only）
3. `build()`：
   - autogen.sh 引导（`env -u CONFIG_SHELL SHELL=/bin/sh /bin/sh -e ./autogen.sh`）
   - `replace_in_file(configure, "umask 077", "umask 022")`（E011/E114，HMDFS 权限）
   - `autotools.configure()` → `os.makedirs(build/doc)` → `autotools.make(-j1)` → `autotools.make(target="check")`（上游 16 用例）
4. `package()`：手工打包（不跑 `make install`）：`bin/{termrec,termplay,termtime,termcat}`、`lib/libtty.a`（libtool 的 `.libs/`）、`include/libtty/{tty.h,ttyrec.h}`、`share/man/man{1,3}/*`、`licenses/COPYING.LIB`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: working directory cannot be determined`（满屏 getcwd 报错） | 设备 profile 把 `SHELL`/`CONFIG_SHELL` 指向 hnp bash，autoconf 经它 re-exec，在 HMDFS 构建目录下 getcwd 失败（E386 §12.38①） | `generate()` 中 `env.unset("CONFIG_SHELL")` + `env.define("SHELL", "/bin/sh")`；autogen/configure/make 全走 /bin/sh |
| 2 | `config.status` 报 `could not setup config files machinery` / `can't create ./conf…/subs1.awk: Permission denied` | config.status 的 `(umask 077 && mktemp -d)` 在 HMDFS 上产生不可写目录（实测：umask 077 → drwx--S--- 不可写；umask 022 → 可写） | ①`replace_in_file` 把 configure 里的 `umask 077` 改为 `022`（E011/E114 受控方案，保留真实临时目录创建）；②mktemp wrapper 也改用 umask 022 建目录 |
| 3 | `checking for lzma_code in -llzma... no` / `ZSTD_compress in -lzstd... no` | `AutotoolsToolchain` 不会自动把依赖 cpp_info 注入 configure 的 CPPFLAGS/LDFLAGS/LIBS，而 configure.ac 用 AC_CHECK_LIB/AC_CHECK_HEADERS 探测 | `generate()` 增加 `AutotoolsDeps(self).generate()`；四个压缩库全部探测为 yes，对应测试用例真实执行而非跳过 |
| 4 | `./conftest: Error loading shared library libzstd.so.1` → `cannot run C compiled programs` | 依赖里 zstd 只提供 shared 库，configure 的 conftest/工具运行期需要它；OHOS musl 忽略 DT_RUNPATH | `generate()` 把各依赖 libdir（绝对路径）prepend 进 `LD_LIBRARY_PATH`（§12.38③） |
| 5 | `ld.lld: error: undefined symbol: pthread_cancel / pthread_setcancelstate` | musl 系 libc（OHOS）不实现 POSIX 线程取消；上游 termplay 以 `pthread_cancel` 管理播放线程与加载线程 | 三个补丁（见下）：autoconf 探测 `HAVE_PTHREAD_CANCEL`，无该能力时改用**协作式停止**（`volatile` 标志 + 唤醒条件变量 + 100ms 分片 `select`；帧写入保持不可打断，等价于原 cancelstate 保护），非空壳 stub |
| 6 | `/bin/sh: can't create doc/libtty.3: No such file or directory` | out-of-source 构建：`doc/Makefile.am` 是 `include` 进顶层 Makefile 而非 SUBDIRS，automake 不会在 build 目录建 `doc/` | `build()` 在 make 前 `os.makedirs(build_folder/doc)`（accel-config 同类 out-of-source quirk 的处理思路） |
| 7 | 消费者测试 `'libtty/tty.h' file not found` | `package_type = "application"` 时 Conan 2 **不向消费者暴露 cpp_info**（实测最小复现：application 类型下 `termrec_INCLUDE_DIRS_RELEASE` 为空，library 类型正常） | 改为 `package_type = "library"` + 声明 `shared` 选项（默认 False，静态 libtty，工具自包含）；CLI 仍随包安装并声明 `commands.json`（R38/PF8） |
| 8 | `libtty.a` 未进包 | libtool 把静态库放在 `.libs/` 下，`package()` 从 build 根目录拷贝扑空 | 从 `build_folder/.libs/` 拷贝（shared 时拷 `libtty.so*`） |

## 源码修改（补丁 3 个）

| 补丁 | 文件 | 内容 |
|------|------|------|
| `0001-configure.ac.patch` | `configure.ac` | `AC_CHECK_FUNCS` 追加 `pthread_cancel pthread_setcancelstate`（可移植能力探测，`HAVE_PTHREAD_CANCEL`） |
| `0002-play-player.c.patch` | `play/player.c` | 无 POSIX 取消能力时：`player_stop` 协作标志 + `cancel_sleep()` 100ms 分片 select + 条件变量唤醒；`replay_stop()` 置位/唤醒/join 后清零；有该能力时保留原 `pthread_cancel` 路径（`#ifdef HAVE_PTHREAD_CANCEL`） |
| `0003-play-termplay.c.patch` | `play/termplay.c` | 退出路径：无取消能力时置 `loader_stop` 并直接 `_exit(0)`（loader 可能阻塞在 read，join 会挂死；`loader_print` 检查标志以免触碰时间线），不释放时间线内存（进程即将退出） |

> 补丁不含任何平台宏（`__OHOS__` 之类）；用的是 autoconf 特性宏，glibc 平台上行为与上游一致。

## 依赖版本
- bzip2/1.0.8、liblzma/5.8.1、zlib/1.3.1.1、zstd/1.5.7（curl 未声明：http/ftp URL 支持按上游逻辑降级为禁用并 WARN）
- 构建期工具（tool_requires）：automake/1.18、libtool/2.5.4（autoconf/m4 用 SDK 自带）

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify termrec 0.19     # Verdict: PASS（G0-G4 + L2/L4/L5）
# 上游 Autotest 套件（make check，配方 build() 内真实执行）
#   All 16 tests were successful.
# 消费者测试（test_package）
#   ALL CHECKS PASSED（15 条断言）
```

- 上游静态用例：**16**（`tests/testsuite.at` 内 `AT_SETUP` 计数：seeks / timeval arithmetics / recording / ttyrec 存取 ×3 / 压缩格式 ×4 / UTF-8 切分 / vt100 ×5）
- 上游实际执行：**16**，通过 **16**，跳过 0（压缩依赖齐备，`.gz/.bz2/.xz/.zst` 四例真实执行）
- 消费者测试（test_package）：1 个程序 / 15 条断言全过（格式注册表、tty 生命周期、ttyrec 录制→读回往返含数据与时间戳断言）；另跑安装后的 `termcat` 做 asciicast→ttyrec 端到端转换

## 注意事项
- 制品为 `termrec/0.19`（含 CLI 工具 + libtty），下游引用：`find_package(termrec)` + `termrec::termrec`，或直接用 `bin/` 下工具
- 默认静态 libtty（工具自包含）；`-o termrec/*:shared=True` 可改为动态库（此时运行期需把包 `lib/` 放进 `LD_LIBRARY_PATH`，OHOS musl 不认 DT_RUNPATH）
- man 页随包安装（设备侧由 harmonybrew 的 pod2man 生成；无 pod2man 的环境该规则会跳过，不影响构建产物）
- curl 未纳入依赖：`http://` 等远端录制地址不可用（上游逻辑本身允许缺省），本地文件/管道录制回放不受影响
---

**编译结束**: 2026-09-16 01:28
**最终状态**: built
