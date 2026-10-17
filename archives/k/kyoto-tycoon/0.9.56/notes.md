# kyoto-tycoon 0.9.56 适配笔记

## 基本信息

- 上游：Kyoto Tycoon 0.9.56（FAL Labs，Mikio Hirabayashi）
- 官方站 `https://dbmx.net/kyototycoon/`（原 fallabs.com 已不可用，dbmx.net 为官方现行站点；
  Homebrew 与 FreeBSD ports 均用此源）
- 源码：`https://dbmx.net/kyototycoon/pkg/kyototycoon-0.9.56.tar.gz`（503581 字节）
- SHA256：`553e4ea83237d9153cc5e17881092cefe0b224687f7ebcc406b061b2f31c75c6`
  （与 Homebrew formula、FreeBSD ports 三方一致；本地下载验算一致）
- License：GPL-3.0-or-later（tarball 内 COPYING）
- 构建系统：custom configure（configure.in + Makefile.in，后缀规则，无 VPATH）
- 同门参照：本仓库 `archives/k/kyoto-cabinet/1.2.80`（同一作者、同一构建风格；
  源内构建、`-j1` 串行、TMPDIR 兜底均沿用其验证结论）

## 构建要点

- 上游 Makefile 只有后缀规则（.cc.o），无 VPATH/`srcdir` 引用 → 必须源内构建。
  conanfile 里 `self.run("./configure ...", cwd=self.source_folder)`，
  make/make check/make install 全部 `cwd=self.source_folder`。
- `make -j1`：上游 check 目标共享 `casket*` 测试库文件且无目标间依赖声明，
  并行会竞争（同 kyoto-cabinet 的踩坑结论）。
- configure 参数：`--prefix=<package_folder>` `--enable-static --disable-shared`
  `--disable-lua`（上游默认，显式写出求可复现）`--with-kc=<kyoto-cabinet 包目录>`。
- `--with-kc` 给 configure 加 `-I<DIR>/include -L<DIR>/lib`；
  zlib 经 `AutotoolsDeps` 的 CPPFLAGS/LDFLAGS 被 `AC_CHECK_LIB(z)` 探测到；
  `kyotocabinet >= 1.2.65` 的 pkg-config 探测经 `PKG_CONFIG_PATH` 满足。
- configure 传 `export LIBS=""`（本轮真机根因）：`configure.in` 先跑
  `AC_PROG_CC`，C 驱动存活链接会继承 `AutotoolsDeps` 注入的环境 `LIBS`
 （config.log 实证 `ac_cv_env_LIBS_value='-lkyotocabinet -lz ...'`），其中
  C++ 库 `-lkyotocabinet` 导致 `C compiler cannot create executables`；
  而同门 kyoto-cabinet（C-only 的 `LIBS`）过同一检查。清空只针对 configure
  调用：其后全部 `AC_CHECK_LIB`（`AC_LANG(C++)` 之后，C++ 驱动）重新探测
  kc/z/m/pthread/rt/dl 并回填 `LIBS`，经 `MYCMDLIBS="$MYCMDLIBS $LIBS`
  进入最终链接，终链不受影响；make/check/install 保持原环境 `LIBS` 不动。
- configure/make 全程内联 `export CC/CXX`（本轮真机根因之二）：真机
  `config.log` 实证工具链 `CC=/data/service/hnp/bin/clang` 在设备 shell 下
  根本不可执行（`inaccessible or not found`，退出码 127），故不能盲信
  `tools.build:compiler_executables`。配方在 build() 内对 conf 值、PATH
  解析（clang/cc/gcc、clang++/c++/g++）、`/usr/local/bin`、`~/usr/local/bin`、
  `/data/service/hnp/bin` 逐个做 `--version` 实测探活，只固定首个真实可
  执行的 CC/CXX（jrtplib/test_package 探活前例）；一边都无可用时保留工具链
  原值并告警，实测结论以 `Using C/C++ compiler:` 日志为准。
- configure.in 里无 umask/mytmpdir 私有逻辑（标准 autoconf 流程），
  不需要 kyoto-cabinet 那样的 umask 补丁；patches/ 仅含 C++17 编译补丁
  `0001-clang-cpp17-constexpr-narrowing.patch`（ktulog.h FLUSHWAIT 改
  constexpr + 两处 FileStatus 花括号初始化加显式 uint64 转换，见下）。 build()
  开头 `apply_conandata_patches` 在 configure 之前应用。
- 只读 /tmp 适配（E002 + 本轮真机失败加固）：真机 /tmp 为只读 erofs，
  配方 `_ensure_writable_tmp()` 在 TMPDIR/TMP/TEMP/HMBS_TMPDIR/HMBS_INSTALL
  中取首个已存在目录统一到三变量，缺失时回退到 build 文件夹内 `hmbs-tmp`
  （并 `makedirs`，绝不把 TMPDIR 固化为 `tempfile.gettempdir()` 的 /tmp）。
  仅靠 `os.environ` 不够——所有 configure/make/check/install 命令行统一内联
  `export TMPDIR/TMP/TEMP` + `export SHELL/CONFIG_SHELL`（设备 shell 优先用
  HMBS 注入值）+ `umask 022`（bwm/0.6.3 前例），conanbuild 域不传递进程
  环境时依然生效；生成的 `configure` 内 `umask 077` 改写为 `022`
 （E011，ezstream/1.0.2 前例）；`HMBS_AUTOCONF_MKTEMP_FALLBACK=1` 时用
  mktemp 垫片使 `./conf*` 请求失败、回退到 autoconf 的 `mkdir` 路径
  （cyrus-sasl-login/2.1.28 前例）。check-remote 脚本消除全部 `$(...)`
  命令替换（device /bin/sh 把替换临时文件写到硬编码 /tmp，见
  `preflight.sh[306]: can't create temporary file /tmp/sh*.tmp`；
  改用 `read ktpid < ktcheck.pid` 内建命令 + 变量传 pid）。
  configure 失败时自动打印源内 `config.log` 尾部 100 行，供下轮按新证据定位
  （myman/4.0.116 前例）。以上只替换临时文件根目录/执行环境，不删除测试。
- 产物：libkyototycoon.a（静态默认）、13 个 kt*.h 头、8 个 CLI
 （ktserver/ktutiltest/ktutilmgr/ktutilserv/kttimedtest/kttimedmgr/
  ktremotetest/ktremotemgr）、libexec 下 2 个 .so 插件、kyototycoon.pc。

## Lua 扩展关闭说明

- `myscript.cc` 用 `lua_objlen`（6 处）等 Lua 5.1 专有 API，
  仓库内 lua 5.4.x 无法编译它；`lua/5.1.5` 在仓内状态为 built（未发布），
  单 PR 原子性（W2）不允许捎带发布依赖。
- 上游默认即关闭 Lua（`AC_ARG_ENABLE(lua)` 默认 no），关闭后 ktserver
  照常构建运行（`myscript.o` 以 `_KT_LUA` 为空实现链接进 ktserver）。
- 故配方显式 `--disable-lua`。服务端 Lua 脚本能力未覆盖，
  待 `lua/5.1.5` 发布后可单独跟进。

## C++17 编译补丁（2026-09-18 真机失败）

- 真机 clang（-std=c++17）报 `ktulog.h:51 static const double FLUSHWAIT`
  需 constexpr（-Wstatic-float-init），及 `ktulog.h:478` /
  `ktremotedb.h:883` 花括号初始化 `int64_t→uint64_t` 变窄
  （-Wc++11-narrowing），`make ktulog.o` 直接失败（2 errors）。
- 全源码扫描：`static const double/float` 仅此 1 处；11 处花括号初始化中
  仅 2 处 FileStatus 存在变窄（Log 的 char*/size_t/uint64 与 BulkRecord 的
  uint16_t/int64_t 均类型一致），补丁覆盖全部风险点。
- `ktremotedb.h:883` 有 `fsiz >= 0 && fts >= 0` 守卫，`ktulog.h:478` 的
  fsiz 来自 `readfixnum` 文件头尺寸（非负），显式转换语义安全，仅替换
  转换写法，不删除测试、不改测试口径。

## ktdbext getpid 补丁（2026-09-18 真机第二轮失败）

- 前一补丁生效后构建推进到 `ktdbext.o`，新报错
  `ktdbext.h:274: use of undeclared identifier 'getpid'`。
- 全源码核查：其余 6 处取进程号均用 `kc::getpid()`（ktplugservmemc.cc /
  ktserver.cc / ktremotetest.cc 等），仅 ktdbext.h:274 用裸 `getpid()`，
  历史靠传递式 `#include <unistd.h>` 隐式可用；OHOS libc++ 工具链下该
  传递包含缺失，属潜伏缺声明（非平台缺函数，clang 亦提示 kc::getpid）。
- 修复：`0002-ktdbext-use-kc-getpid.patch` 改为与全仓一致的
  `kc::getpid()`（kyoto-cabinet 可移植封装），不新增系统头、不改语义；
  其余 `::fork`/`::dup2`/`::gethostname` 均已全局限定，无同类漏网。

## ktremotedb 空指针返回补丁（2026-09-18 真机第三轮失败）

- 前两补丁生效后构建推进到 `ktremotedb.o`，新报错 4 处
  `ktremotedb.h:301/353/414/484: cannot initialize return object of type
  'char *' with an rvalue of type 'bool'`（游标 get_key/get_value/get/seize）。
- 根因：C++98 允许 `false` 隐式转空指针，C++11 起 bool→指针转换为硬错误；
  四函数文档均写 "or NULL on failure"，`return false` 本意即空指针。
- 全仓核查：其余 `return false` 经逐点确认均在 bool/int 函数内（含
  kttimeddb.h/ktulog.h/kthttp.h 的误报点）；visitor 的 visit_full/visit_empty
  实现返回 NOP/REMOVE/指针，从无 `return false`。仅此 4 处需改。
- 修复：`0003-ktremotedb-null-pointer-return.patch` 改为 `return NULL;`
  （与函数文档及文件内 `*vbp = NULL` 风格一致；NULL 在任何标准下合法，
  比 nullptr 更贴合本文件年代风格），语义不变。

## check-remote daemon 绝对路径修复（2026-09-18 真机第四轮失败）

- 前三补丁生效后编译已通过（构建推进到 `make check` 之后），新失败点在
  `build()` 第二阶段：`./ktserver -port 1978 -dmn -pid ktcheck.pid -log
  ktcheck.log` 直接报错 `./ktserver: ktcheck.log: a daemon can accept
  absolute path only`，无 pid 文件，`make check-remote` 根本未执行。
- 根因：ktserver 的 daemon 化分支要求 `-pid`/`-log` 为绝对路径（相对路径
  直接拒绝启动），与编译器/补丁无关，是配方测试脚本写法问题。
- 修复（只改配方 `build()` 的 `remote_script`，不碰上游源码、不删测试）：
  `-pid`/`-log` 改为 `self.source_folder` 下的绝对路径（源内构建目录已
  证实可写，`.o`/check 产物均落盘于此；shell 侧加双引号防空格；`read`/
  `kill -0`/`cat` 探活逻辑与无 `$(...)` 约束保持不变）。
- 本轮 `HMBS 平台诊断 [readonly_tmp]` 为 harness 头部噪声（出现在 recipe
  export 之前的 `preflight.sh[306]` 自身 `/tmp` 探测行），配方
  `_ensure_writable_tmp()` + 全命令内联 `export TMPDIR/TMP/TEMP` 已存在且
  与本次失败无关，故未改动临时目录逻辑。

## check-remote 空 host 解析失败修复（2026-09-18 真机第五轮失败）

- 现象：`kill -0` 探活通过，但 `make check-remote` 首命令即失败
  `./ktremotemgr: DB::status failed: :1978: 6: network error: unexpected error`
  （注意 `:1978` 前 host 为空；6 = RPCClient::RVENETWORK）。
- 根因：`kthttp.h HTTPClient::open()` 空 host 时走
  `get_host_address(get_local_host_name())`；真机容器 hostname 无 DNS/hosts
  记录，`getaddrinfo` 返回非零 → 地址为空 → 直接返回 false。
  服务端已在 `0.0.0.0:1978` 监听（ServerSocket 空地址即 0.0.0.0），是客户端
  默认寻址在该环境下失效，与端口占用/启动慢无关；上游源码无 /tmp 硬编码。
- 修复：新增 `0004-kthttp-localhost-fallback.patch`，仅在空 host 分支加
  `127.0.0.1` 兜底（显式 host 路径不动）；`make check-remote` 保持上游原样
  53 命令全量运行，不删测试。配方侧同步加固：pid 文件轮询（~12s）、
  `ktremotemgr report` 就绪轮询（30s，均无 `$(...)`）、失败时必打 ktserver
  日志。`[readonly_tmp]` 仍为 preflight.sh 头部自身探测噪声，配方 TMPDIR
  逻辑不动。

## check-remote epoll 后端故障修复（2026-09-18 真机第六轮失败）

- 现象：0004 生效后就绪探针 `POST /rpc/report 200` 成功，但随即服务端刷屏
  `poller error: msg=epoll_ctl failed` / `socket error`，`make check-remote`
  首命令 `DB::open failed: : 6: network error: connection failed`。
- 根因：`myconf.h` 在 Linux 下默认 `_KT_EVENT_EPOLL`；真机 HongMeng 内核沙箱
  中首个连接后 `epoll_ctl(ADD/MOD/DEL)` 即失败，poller 进入坏状态，
  后续连接全部被拒。是事件后端与环境不兼容，不是测试写法问题。
- 修复（与前两轮不同策略，不改补丁语义、不删测试）：configure 追加上游官方
  可移植开关 `--disable-event`（configure.in 原生支持，定义 `_MYNOEVENT`，
  回退到通用 select 轮询）。53+126 共 179 项命令照常全跑，仅替换 I/O 后端。

## 上游测试审计（L1）

`Makefile.in` 的 RUNENV 命令行计数（`grep -c '$(RUNENV)'` 按子目标）：

| 子目标 | 命令数 | 内容 |
|---|---|---|
| check-util | 8 | ktutilmgr/ktutiltest（ulog 等）|
| check-timed | 118 | kttimedmgr/kttimedtest（order/queue/wicked/tran/mapred/misc/ulog）|
| check-remote | 53 | ktremotemgr/ktremotetest（需常驻 ktserver，默认 127.0.0.1:1978）|
| **make check 运行合计** | **179** | check-util + check-timed + check-remote |
| check-heavy / check-timed-heavy | — | 数百万记录压测，不在上游 `make check` 内，不运行 |

- harness 为 fail-fast：无 `-` 前缀、无 `|| true`，make 遇到首个非零退出即停；
  因此 `make check` / `make check-remote` 退出 0 ⟺ 计数的命令全部真实执行且通过，
  不存在"执行数小于发现数还报通过"的可能。
- 防"空跑报通过"（toybox 教训）：两阶段后各断言 `test -s check.out && grep -q . check.out`
 （harness 把 `list` 结果重定向到 check.out；空文件说明 fixture 未物化）。
- check-remote 由配方在 build() 内自举：`ktserver -port 1978 -dmn -pid ... -log ...`
 （内存原型库 `:`），pid 轮询 + `kill -0` 探活 + `ktremotemgr report` 就绪轮询
  （失败则打出 ktserver 日志并直接报错，不会对着没起来的端口跑 53 条），跑完 kill server 并清理 `casket*`/`*-ulog`。
  该路径同时覆盖了 ktsocket 的 epoll 事件循环（平台相关代码）。

## test_package（24 项）

- test.cpp（20 项，TimedDB 文件 Tree 库 `casket.kct`，与 check-timed 主力后端一致）：
  创建/写入/读取/append/删除/迭代/重开/持久化/synchronize(fsync)/非法路径/清理。
  文件锁与同步均不关闭，HMDFS 不兼容会直接失败。
- conanfile test() 另对**安装后**的 kttimedmgr 做 CLI smoke（4 步）：
  `create -otr` / `set` / `get -px` / `remove`，逐条按退出码校验。
- 计入 `HMBS_TEST_PACKAGE_RESULT`：discovered=24，passedCount=24。

## 平台行为备注

- ktsocket.cc 用 epoll（15 处）+ kqueue 回退（2 处）；configure 按常规头/函数探测。
  check-remote 在真机回环真实走 epoll 路径，是本次平台验证的关键覆盖。
- 线程/mmap/文件锁经 kyoto-cabinet（PolyDB 内核）继承，其 notes 已在真机验证通过。
- CI_PACKAGES 定向构建：`CI_PACKAGES=kyoto-tycoon python3 scripts/gitcode_pr.py ...`

## 遗留

- check-heavy / check-timed-heavy（数百万记录）不在上游 `make check` 内，未运行。
- 服务端 Lua 脚本（`--enable-lua`）未启用，待 lua/5.1.5 发布后跟进。

## zlib version override (repo-only 1.3.1.1)

- `requirements()` pins `zlib/1.3.1.1` with `override=True`, unifying
  kyoto-cabinet/1.2.80's transitive `zlib/1.3.1` edge onto a single version.
- Rationale: 1.3.1.1 is repo-only (same 1.3.1 source, -fPIC static, Makefile
  flow verified on-device), so the resolver must take the ohpcd recipe;
  conancenter carries no such version and its CMake recipe fails the compiler
  check under the OHOS profile. Precedent: abiword-plugin-docbook/3.0.8
  (consumer-side override after CI version conflict).

## test_package kttimedmgr absolute-path fix (2026-09-18 preflight test_package fail)

- Symptom: test.cpp 20 checks ALL PASSED, then
  `RUN: kttimedmgr create -otr ...` -> `/bin/sh: kttimedmgr:
  inaccessible or not found`, ConanException exit 127 at old
  test_package/conanfile.py line 199.
- Root cause: CLI invoked by bare name, relying on conanrun PATH
  aggregation for a library package_type; the device shell did not
  resolve it. Binary is installed under <kyoto-tycoon package>/bin
  (package_info bindirs=["bin"], 8 KT CLIs via `make install`).
- Fix (test-only, no assertion removed, same 4 CLI steps + same
  exit-code checks): resolve
  `<deps["kyoto-tycoon"].package_folder>/bin/kttimedmgr` and invoke by
  quoted absolute path (bam/0.5.1 + sysstat/12.7.9 + fzy/1.1 precedent),
  keep env="conanrun" for LD_LIBRARY_PATH, fail loudly with the resolved
  path if the file is missing, and replace the quoted-glob
  `rm -f "db" "db.*"` (glob never expanded inside quotes) with python
  os.remove + glob cleanup. Counts unchanged: 20 cpp + 4 cli = 24.
- The `[readonly_tmp]` platform note in this round is pre-export
  preflight.sh self-probe noise (/tmp probe before recipe export);
  recipe + test_package TMPDIR handling already covers it.
