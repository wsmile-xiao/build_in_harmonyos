# serf 1.3.10 适配笔记

## 编译环境
- 构建系统: scons（SCons 4.10.1，generate 阶段隔离 pip 安装，gpsd/3.26 同款模式）
- 编译日期: 2026-09-20
- 编译器: clang
- 状态: built（待真机预检回填实测证据）

## 编译步骤

1. `get` 下载 `serf-1.3.10.tar.bz2`（archive.apache.org 主源 + downloads.apache.org 回退，同文件同 sha256）。
2. generate 阶段把 SCons 4.10.1 pip 安装到构建目录 `_scons_env`，经 `scons_env` 脚本注入 `PYTHONPATH`；并把 SCons POSIX 平台 `SHELL` 改为 `/system/bin/sh`（OHOS 无 `/bin/sh`）。
3. build 阶段先以官方 apr-util-1.6.3 源码在构建目录完成私有静态子构建（`configure --with-apr=<apr-1-config文件> --with-expat=<expat包>` + 显式 `--build/--host`，以 Python 复刻仓内三补丁：`__OHOS__`/ohos-linux/umask022；`_resolve_apr_build_dir()` 先校验 `apr-1-config --installbuilddir` 并在缓存重定位失效时于 apr 包内搜索真实 `apr_rules.mk`，configure 后若 `build/rules.mk` 缺失则从校验位置补拷），安装到构建前缀 `apu/`；再以 `python3 -m SCons -Y <src> --jobs=1 APR=<apr包> APU=<构建前缀apu> OPENSSL=<openssl包> ZLIB=<zlib包> PREFIX=<包> LIBDIR=<包>/lib DEBUG=False APR_STATIC=True CC=clang CFLAGS="-fPIC -O2" LINKFLAGS/CPPFLAGS/LIBS（依赖闭包聚合）` 编译出 `libserf-1.a` 与 `libserf-1.so`。
4. 同一阶段运行 `python3 -m SCons check` 执行上游完整测试（见“验证结果”），解析输出后把证据 JSON 落盘 `upstream_test_result.json` 并随包发布到 `res/`，供 test_package 重发标记。
5. package 阶段运行 `scons install`，按 shared 选项裁剪另一链接形态的产物（私有 `libaprutil-1.a` 始终保留）；把构建前缀 `apu/lib/libaprutil-1.a` 合入包内 `lib/`，`package_info.libs` 为 `["serf-1", "aprutil-1"]`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | registry 无 scons 配方，无法 `tool_requires` | scons/4.10.0 在仓内仅有元数据目录，无 conanfile | 沿用 gpsd/3.26 验证过的隔离 pip 安装模式（`_scons_env` + `PYTHONPATH`），build 内零网络调用 |
| 2 | SCons 派生 shell 在 OHOS 失败 | OHOS 无 `/bin/sh`，SCons POSIX 平台默认 `SHELL=sh` | generate 阶段把已安装 SCons 的 posix 平台 `SHELL` 改为 `/system/bin/sh` |
| 3 | zlib 头文件/库目录未进入编译 | SConstruct 只加 `$OPENSSL/include` 与 `$OPENSSL/lib`，不处理 ZLIB 路径 | 从 Conan 依赖闭包聚合全部 includedirs/libdirs/libs，经 `CPPFLAGS`/`LINKFLAGS`/`LIBS` 传入 |
| 4 | 编译器必须来自 Conan 配置 | R33 禁止裸用 shell 的 `CC`/`CFLAGS` | 经 `tools.build:compiler_executables` 读取并校验可执行性，缺失时回退 PATH 查找 clang/cc/gcc |
| 5 | `scons check` 退出码 0 不等于真跑 | 需防空 fixture 假通过（toybox tar-B 教训） | 校验 5 个 `.response` fixture 非空并与 `== Testing` 行数交叉核对；CuTest 进度字符数与 `OK (N tests)` 交叉核对 |
| 6 | 真机 /tmp 只读，pip/SCons 临时文件失败 | HarmonyOS PC 的 /tmp 只读，pip 缓存与 SCons/check.py 会回退到 /tmp | generate/_scons_env 复用 HMBS 注入的 TMPDIR/TMP/TEMP（缺失回退 build/_tmp），pip 加 --cache-dir，不假设 /tmp 可写 |
| 7 | 同上，test_package 编译/运行 shell 阶段同样面临只读 /tmp | `cc` 编译与 `sh -c test_serf` 子进程继承进程环境，/tmp 不可写会同类失败 | test_package 的 build()/test() 入口复用可写临时目录并导出 TMPDIR/TMP/TEMP，仅环境变量改动，用例数与标记口径不变；图计算缺 apr-util 制品仍属 W0/R36 阻塞（上游主干核验无该配方），待依赖发布后复跑 |
| 8 | 图计算缺 apr-util 与前三轮同指纹复现；前三轮 TMPDIR 加固均作用于图计算之后、无效果，且直连双 pin（apr + apr-util）偏离上游规范 | generate()/_scons_env/test_package 的 TMPDIR 逻辑只在图计算成功后执行，图失败时根本不会运行，故包哈希变化但失败点不变；另直连 apr/1.7.6 与 conan-center serf 规范（仅需 apr-util，apr 传递）不一致，apr-util 发布后仍可能版本冲突 | 对齐规范：删除直连 `apr/1.7.6` pin，apr 经 apr-util 传递进入闭包（`self.dependencies["apr"]` 对传递依赖仍可用，SConstruct 的 APR/APR_STATIC 取值不变）；apr-util/1.6.3 pin 保持（与 archives/a/apr-util/1.6.3 一致）；测试口径与标记不变；远端缺 apr-util 制品仍需后端先发布，本改动只消除将来的冲突类失败 |
| 9 | 上轮去直连 apr pin 已同步生效（预检 Requirements 不再列 apr）但图计算仍报 apr-util 缺失；同指纹下不得重复旧策略 | 全仓无任一合入配方 requires 任何 apr-util（确无已发布替代版本）；expat/2.8.2 被 wayland/pulseaudio/polkit 等大量合入配方引用（已发布）；实测上游 apr-util-1.6.3 包内无 bundled expat，必须外供 expat；configure 证据表明 ldap/dbm/crypto 均为 opt-in，`--with-expat` 必须给目录 | 私有子构建：source() 增下官方 apr-util-1.6.3（archive+dlcdn 双官方镜像，已验证 sha256），build() 内以 Python 复刻仓内三补丁（`__OHOS__`/ohos-linux/umask022，无需 patch 二进制）后 `configure --with-apr=<apr包> --with-expat=<expat包> --disable-shared --enable-static` 安装到构建前缀，SCons APU 指向该前缀；package() 合入 `libaprutil-1.a` 并在裁剪时保留，`package_info.libs` 追加 `aprutil-1`；单 archives 目录未增，测试口径与标记不变 |

| 10 | 私有 apr-util `configure` 报 `cannot guess build type`（真机预检 compile 阶段） | 未传三元组时旧版（2021）config.guess 在真机上无法识别 HongMeng 内核，`checking build system type...` 直接失败 | 新增 `_apu_triplets()` 由 settings 派生三元组（armv8→aarch64；OHOS 用 stock config.sub 可接受的 `*-unknown-linux-gnu`，原生构建 build==host），configure 显式传 `--build/--host` 绕过 config.guess（zzuf/owfs/bacula 同款模式）；既有 config.guess/sub/umask 补丁与 TMPDIR 加固保留，测试口径与标记不变 |
| 11 | 私有 apr-util `configure` 后 `make` 报 `build/rules.mk: No such file`，伴随 `configure[4671]: cd: //build-1` 与 `cp: cannot stat '/apr_rules.mk'`（真机预检 compile 阶段） | `apr-1-config --installbuilddir` 返回本机不存在的目录（远端缓存重定位后构建期绝对路径失效）；apr-util configure 仅用它做一次 `cp $APR_BUILD_DIR/apr_rules.mk`（非 AC_SUBST），失败也不退出，导致 Makefile 缺 rules.mk；另 `--disable-shared/--enable-static` 非 apr-util 选项（仅告警） | 新增 `_resolve_apr_build_dir()`：显式定位 `bin/apr-1-config` 并执行 `--installbuilddir`，校验目录及 `apr_rules.mk`，失效时在 apr 包内搜索真实位置（优先 `build-1/`）；`--with-apr` 改传配置文件路径；删除两个不支持的开关；configure 后若 `build/rules.mk` 仍缺失则从校验位置补拷（configure 该 cp 的等价重放，无 wrapper 脚本，无 exec 位风险）；测试口径与标记不变 |
| 13 | 真机 configure 报只读 /tmp（/tmp/sh*.tmp: Read-only）后 can.t fork，私有 apr-util 构建失败（真机预检 compile 阶段） | 旧 TMPDIR 逻辑只做 makedirs/isdir、无真实写入探测，可能复用不可写目录；且未处理 HMBS_AUTOCONF_MKTEMP_FALLBACK=1 下 mktemp 建目录不可写、进程 umask 未固定、configure 失败无 config.log 证据 | _hmbs_tmpdir/_scons_env/test_package 改为写入探测（makedirs+open+unlink）并纳入 HMBS_TMPDIR/HMBS_INSTALL 候选；新增 _device_shell/_mktemp_fallback_shim（cyrus-sasl-login/kyoto-tycoon 同款，仅 FALLBACK=1 时对 conf* 影子 mktemp）；_build_apr_util 固定 os.umask(022)、显式导出 TMPDIR/TMP/TEMP/CONFIG_SHELL/SHELL、shim 前置 PATH，configure 失败自动落 config.log 证据；测试口径与标记不变 |

| 12 | rules.mk-only repair left `//build-1/libtool` failing plus HNP bash getcwd errors (compile) | apr-1-config relocation bakes bogus `//build-1`/`//include` into every generated Makefile, not just build/rules.mk; HNP bash cannot getcwd on HMFS cache while /bin/sh can (configure via sh clean) | _resolve returns bogus dir too; new _repair_apr_relocation rewrites bogus build/include/lib tokens in all generated files and verifies real libtool; make/install pinned to SHELL=/bin/sh via env plus make arg, cwd stays at src; supersedes round-2 copy-only fix; test scope unchanged |
| 14 | 真机 compile 阶段 `tar (child): Cannot fork: Out of memory`（2026-09-20 预检） | 受限设备内存压力下 tar/bzip2 子进程 fork 失败；配方内 SCons/apr-util 子构建已是 --jobs=1，但构建/test 子进程未显式约束压缩线程，且 generate 留下的 pip-cache 与双源码归档并存占用磁盘/内存 | _scons_env 全量子进程显式 setdefault MAKEFLAGS=-j1、XZ_OPT=-T1、XZ_DEFAULTS=-T 1（不覆盖已有测试环境）；generate 安装 SCons 后即清理 pip-cache（保留 _scons_env）；测试口径与标记不变 |
| 15 | 真机 compile 阶段 `scons: *** Error converting option: 'DEBUG' / Invalid value for boolean variable: '"False"'`（2026-09-21 预检） | `_scons_args()` 用 `esc()` 给每个值加双引号再以 list 形式 `subprocess.run`（无 shell），引号成为字面值，SCons BoolVariable 收到 `'"False"'` 拒绝；LINKFLAGS/CPPFLAGS 内层单引号同理多余 | 删除 `esc()`，`KEY=value` 原样传参（单 argv 元素已保留空格），标志改 `-L%s`/`-I%s` 无内层引号；测试口径与标记不变 |
| 16 | 真机 compile 阶段 `/system/bin/sh: ar: inaccessible or not found / scons: *** [libserf-1.a] Error 127`（2026-09-21 第二轮预检，引号修复后） | CC 为绝对路径故编译通过，但 SCons 以裸名 `ar` 经 `/system/bin/sh` 归档，该 shell 的 PATH 缺 harmonybrew 工具链目录；与 getcwd 噪声无关（SCons 已正常编译出 ssl_buckets 警告，cwd 可用） | 新增 `_ar_ranlib()`：AR/RANLIB 按环境覆盖→CC 同目录（llvm-ar/aarch64-linux-ohos-ar/ar 等）→PATH 顺序探测并显式经 SCons 参数传入；`_scons_env()` 前置 CC 目录到 PATH 兜底裸名调用；测试口径与标记不变 |
| 18 | SConstruct patch honors AR/RANLIB + ENV PATH (compile Error 127 third round, 2026-09-21) | SConstruct opts has no AR/RANLIB so cmdline AR is unknown-var-ignored; SCons runs archive via env ENV PATH not process PATH, so shim/process-PATH never took effect | _patch_sconstruct_archiver idempotent Python edit after Environment: ARGUMENTS AR/RANLIB (fallback AR/HMBS_AR environ) into env AR/RANLIB + caller PATH into env ENV PATH; _scons_env drops symlink shim, keeps CC-dir PATH prepend + exports AR/RANLIB; build calls patch before apr-util/SCons; test scope unchanged |
| 17 | 同指纹第三轮：显式 `AR=/.../llvm-ar RANLIB=/.../llvm-ranlib` 已传入仍报裸名 `ar` 缺失（2026-09-21 预检，`archiver probe ... exit 0` 后仍 `Error 127`） | SConstruct 忽略命令行 AR 覆盖（仍以裸名 `ar` 经 `/system/bin/sh` 调用）；仅传绝对路径不够，必须让裸名本身可解析 | 不同策略：`_scons_env()` 在构建目录建 `_ar_shim/`，以 symlink（失败回退 hardlink）发布裸名 `ar`→llvm-ar、`ranlib`→llvm-ranlib，并把 shim 目录与 CC 目录前置到 PATH；保留显式 AR/RANLIB 传参作双保险；测试口径与标记不变 |

| 19 | CI #54842 SCons 读取阶段 TypeError can't concat str to bytes（SConstruct line 418 os.popen read，<frozen codecs> line 321），scons exit 2，未开始编译即中止（2026-09-22 CI） | 上游1.3.10以os.popen捕获apr-1-config/apu-1-config --link-libtool --libs输出，该worker的python3下os.popen的read()在codecs层抛bytes/str拼接TypeError；与AR/RANLIB未知变量告警无关（该告警无害，补丁仍消费ARGUMENTS） | 新增_patch_sconstruct_popen()（经_patch_sconstruct_static_only()尾部调用，新旧源码树全覆盖）：幂等Python字符串补丁，以subprocess.run(shell=True、stdout=PIPE、stderr=DEVNULL)加显式bytes->str解码替代os.popen，失败返回空串（仅pkg-config LIBS行降级，不中止构建）；stderr不合并以保持与os.popen一致；测试口径与标记不变 |

## 源码修改

无。serf 1.3.10 已原生兼容 Python3（SConstruct 含 `.decode()` 修复）与 OpenSSL 3（`USE_OPENSSL_1_1_API` 在 `OPENSSL_VERSION_NUMBER >= 0x10100000L` 时自动定义，覆盖 1.1.x 与 3.x；`ERR_GET_FUNC` 已无引用），`conandata.yml` 无 patches。

## 依赖版本

- apr/1.7.6（直连；远端已发布，真机缓存命中，为私有 apr-util 子构建与 SCons 提供 apr-1-config）
- expat/2.8.2（直连；被 wayland/pulseaudio/polkit 等大量合入配方共同引用的已发布版本，供私有 apr-util `--with-expat`；apr-util 1.6.x 已无 bundled expat）
- apr-util/1.6.3（私有静态子构建：官方源码包 + 已验证 sha256，不走远端 requires；SCons 的 APU 指向构建前缀，产物 libaprutil-1.a 合入本包 lib/）
- zlib/1.3.1
- openssl/3.5.6

## 验证结果

```bash
# 真机预检（conan create）待运行；通过后回填：
# - scons check：5 fixture + 72 CuTest（context 31 / buckets 26 / ssl 6 / auth 9）
# - test_package ./test_serf：8 项 API 检查
# HMBS_TEST_PACKAGE_RESULT / HMBS_UPSTREAM_TEST_RESULT 以预检 stdout 实测为准
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libserf-1.a（默认）或 lib/libserf-1.so | 静态/共享库（二选一，随 shared 选项） |
| include/serf-1/serf.h 等 | 公共头文件 |
| res/upstream_test_result.json | 上游测试实测证据（test_package 重发标记用） |

## 注意事项

- 默认静态构建（`shared=False`）；SCons 每次同时构建两种形态，package 阶段裁剪未选项。
- apr-util/1.6.3 的制品仓状态需预检确认；若缺失，serf 适配阻塞，需按 W0/R36 先合入 apr-util 配方。
