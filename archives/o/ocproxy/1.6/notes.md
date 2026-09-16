# ocproxy 1.6 适配笔记

## 编译环境

- 构建系统：autotools（上游 tarball 只带 `configure.ac`/`Makefile.am`，无预生成 `configure`）
- 目标：OHOS / HarmonyOS PC aarch64（`os=OHOS`、`os.version=6.0`、`arch=armv8`、clang 15）
- 编译器：`/data/service/hnp/bin/clang`（由 `AutotoolsToolchain` 注入，配方不写死路径）
- 依赖：`libevent/2.1.13`（已发布 binary）；lwIP 与 lwIP unix contrib port 随 tarball vendored
- 构建工具依赖：`automake/1.18`（`tool_requires`，提供 `aclocal`/`automake`；原因见下方第 7 条）
- 构建日期：2026-09-13
- 版本口径：包目录与制品版本取任务卡值 `1.6`（CI L0n 按「分支名去前缀 == 包目录名-版本」精确匹配）；
  上游 tag 是 `v1.60`、`configure.ac` 的 `AC_INIT` 声明 `1.60`，因此产物自报版本为 `1.60`
  （`ocproxy --version` 打印 `1.60`，测试断言也按 `1.60`）。三者关系已在下文与
  `conandata.yml` 注释中说明；若后续需要递增后缀修复，目录/制品按 `1.6.N` 走。

## 编译步骤

配方 `build()` 的实际顺序（`reports/conan-create-log.md` 是逐字日志）：

1. `apply_conandata_patches()` —— 应用两个补丁（`Apply patch` 行在日志中可见两次）。
2. `autoreconf --force --install --verbose`（`cwd=source_folder`）—— 生成 `configure`、
   `Makefile.in`、`config.guess`/`config.sub`/`install-sh`/`missing`/`depcomp`。
3. 就地去掉 `configure` 里 autoconf 生成的 `(umask 077 && mktemp -d "./confXXXXXX")`。
4. `Autotools.configure(args=["--build=aarch64-linux-ohos", "--host=aarch64-linux-ohos"])`。
5. `Autotools.make(args=["-j1"])` —— 设备内存紧张（实测 `MemFree` 只有数百 MB），
   且 HMDFS 上 make jobserver 的 FIFO 不可靠，因此固定单作业。
6. `Autotools.install(args=["-j1"])`（与 build 同为单作业），再补 `LICENSE`，并对
   `bin/ocproxy`、`bin/vpnns` 同时断言「存在 + 可执行位（`os.access(..., X_OK)`）」。

## 补丁

| 文件 | 内容 | 依据 |
| --- | --- | --- |
| `patches/0001-src-ocproxy.c.patch` | 给 `ocproxy` 补 `#include "config.h"`（`PACKAGE_VERSION` 来源）、`-V/--version`、`-h/--help`，并预扫描 `argv` 让这两个开关在 `VPNFD` 检查之前生效 | 上游 `vpnns` 1.60 已有同一形态的 `--version`/`--help`；缺这两个开关时打包与冒烟检查无法在无隧道环境下识别产物 |
| `patches/0002-src-vpnns.c.patch` | `vpnns` 的 `get_current_dir_name()` → `getcwd(NULL, 0)`（等价 POSIX 替换）；**行为变更**：无参运行改为打印用法并退出 1 | OHOS libc 既无该声明也无该符号；上游 `do_app()` 在无参时会经命名空间创建路径去启动 `$SHELL`，在本设备上先段错误（实测 rc=-31）。该守卫因此**覆盖了上游「无参即交互 shell」的语义**：vpnns 在本平台的定位是 `-- <command>` / `--attach` 运行器，隐式 shell 需要命名空间特权，包内测试改为断言「失败闭合」；此项已写入 `conandata.yml` 的 `patch_description` 并在 PR 正文单列 |

两个补丁都用 `patch_ng.fromfile(...).apply(strip=1, root=<独立 pristine 副本>)` 验证过，
应用结果与生成补丁的 work 树逐字节一致（`diff -r` 除追踪器文件外无差异）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
| --- | --- | --- | --- |
| 1 | `configure: error: cannot guess build type; you must specify one` | `config.guess` 不认识 `uname -s` 报出的 `HarmonyOS`，而且它的编译探测需要 `cc`，设备上没有 | 显式传 `--build=aarch64-linux-ohos --host=aarch64-linux-ohos`（`config.sub` 认识这个三元组），两者相同 → configure 仍是 native 模式 |
| 2 | `./config.status: line 612: ./confiziVXM/subs1.awk: Permission denied` | autoconf 生成的 `configure` 用 `(umask 077 && mktemp -d)` 建私有临时目录；HMDFS 下该目录属性为 `drwx--S--- 2700`，连创建它的同一进程也写不进去（实测复现） | 补丁：生成 `configure` 后就地去掉这两处 `umask 077`；`TMPDIR`/`TMP`/`TEMP` 同时指向 build 目录内的可写子目录 |
| 3 | `configure: error: cannot run C compiled programs`（`config.log` 内真实首错是 `Error loading shared library libevent_extra.so`） | `AutotoolsDeps` 只注入 `-L`/`-l`，rpath 分支仅在 macOS 生效，所以 configure 的 C 编译器可用性探针与 `AC_CHECK_LIB(event_add)` 都因加载器找不到 libevent 而失败 | 在 build 环境里把依赖包的 `lib` 目录前置到 `LD_LIBRARY_PATH`（用 `self.dependencies["libevent"].package_folder`，不写死缓存路径） |
| 4 | `make` 报 `error: incompatible integer to pointer conversion assigning to 'char *' from 'int'`（`src/vpnns.c`） | `get_current_dir_name()` 是 GNU 扩展，OHOS libc 没有；隐式声明返回 int，被上游自带的 `-Werror=int-conversion` 拦下 | 补丁：改用 `getcwd(NULL, 0)`（POSIX，返回 malloc 分配的绝对路径，与后面的 `free(pwd)` 一致） |
| 5 | `vpnns` 无参运行时 coredump（rc = -31） | 上游 `do_app()` 在命令缺失时仍走命名空间创建路径，随后解引用不存在的命令 | 补丁：`optind >= argc` 时打印用法并返回 1（失败闭合） |
| 6 | `PACKAGE_VERSION` 未声明，编译失败 | `src/ocproxy.c` 从不 `#include "config.h"`，autoconf 只通过 `DEFS=-DHAVE_CONFIG_H` 提供它 | 补丁：补上 `#include "config.h"`（`src/vpnns.c` 本来就包含它） |
| 7 | CI worker 上 `autoreconf: error: aclocal failed with exit status: 2`（`Can't exec "aclocal": No such file or directory`） | 设备上 `aclocal` 来自 `~/.harmonybrew/bin`，而 CI worker 的 PATH（`/data/app/bin:/system/bin:/system/sbin:/vendor/bin:...`）里既没有 harmonybrew 也没有系统 automake，`autoreconf` 找不到 `aclocal` | 加 `build_requirements()` → `self.tool_requires("automake/1.18")`：该包的 `package_info()` 导出 `ACLOCAL_PATH`/`AUTOMAKE`/`ACLOCAL`/`PERL5LIB`，perl 入口点不依赖宿主环境（与仓库 `abx` 配方同法）。修复后用「去掉 harmonybrew 的短 PATH」在设备上复现验证：`aclocal`/`automake` 均为 MISSING 仍能通过 G2 且 test_package 17/17；CI #45483 随后变绿 |

## 端到端验证的实测细节

- **隧道用 socketpair 而不是 pipe**：`os.pipe()` 的写端在 HMDFS 上即使有数据也不会被
  `select()` 报告可读（实测 `bytes_read_from_tunnel=0`），换成 `socket.socketpair()` 后同一
  请求读到 **227 字节**。这是留档口径，避免后续把「读到 0 字节」误判成协议栈没工作。
- **SOCKS5 真实握手**：向 `-D` 监听端口发 `05 01 00`，收到 `05 00`；随后发
  `CONNECT 192.0.2.1:80`，ocproxy 接受请求并把 lwIP 生成的报文写进隧道（伪造 VPN 端不会回
  SYN-ACK，所以 SOCKS 应答按设计不会到达，测试据此判「已交给隧道」而不是「已连通远端」）。
- **`-L` 真实监听**：`-L 18081:example.invalid:22` 拉起本地监听端口并可建立 TCP 连接。

## 依赖版本

| 依赖 | 版本 | 来源 | 说明 |
| --- | --- | --- | --- |
| libevent | 2.1.13 | ohpcd（已发布 binary） | `conan install --requires=libevent/2.1.13 --build=never` rc = 0 |
| lwIP | 随 tarball vendored | 上游 tarball | 不参与外部依赖链 |

R26（系统同名库静态链接）不适用：设备 `/system/lib64` 只有 `libeventEmitter.z.so`、
`libeventhandler_native.z.so`、`libeventloggerso.z.so`，SDK sysroot 里没有任何 `libevent*`，
即不存在同名系统库；仓库内 `bitcoin`、`coturn`、`coeurl` 等已适配包同样动态链接该依赖。

## 验证结果

`conan create` 的 test_package 段（最终 SHA）：

```text
== package layout ==
  [PASS] ocproxy installed and executable
  [PASS] vpnns installed and executable
== failure modes ==
  [PASS] missing VPNFD fails closed
  [PASS] non-numeric VPNFD fails closed
== live proxy behaviour ==
  [PASS] -D SOCKS5 listener accepts connections
  [PASS] -L port-forward listener accepts connections
  [PASS] SOCKS5 no-auth negotiation answered :: 0500
  [PASS] SOCKS5 CONNECT accepted for tunnel delivery
  [PASS] SOCKS5 request produced tunnel traffic :: bytes_read_from_tunnel=227
  [PASS] malformed -D fails closed
  [PASS] truncated -L fails closed
== version and help switches ==
  [PASS] ocproxy --version works without a tunnel
  [PASS] ocproxy -V short form works
  [PASS] ocproxy --help lists the tunnel options
== vpnns ==
  [PASS] vpnns -h prints usage and exits 1
  [PASS] vpnns -v prints version and exits 0
  [PASS] vpnns without a command fails closed
TOTAL=17 PASS=17 FAIL=0
```

上游测试：本包构建运行的上游测试为 `0/0`（上游无可运行测试入口），清点与归因见
`reports/upstream-test-inventory.md`。

## 交付物

| 文件 | 说明 |
| --- | --- |
| `bin/ocproxy` | 用户态 SOCKS5 代理与端口转发主程序 |
| `bin/vpnns` | 实验性命名空间运行器 |
| `share/man/man1/ocproxy.1`、`share/man/man1/vpnns.1` | 上游手册页 |
| `share/doc/ocproxy/README.md`、`share/doc/ocproxy/CHANGES` | 上游文档 |
| `licenses/LICENSE` | 上游 BSD-3-Clause 许可证 |

## 注意事项

- 两个二进制都动态链接 libevent，运行期需要 `libevent` 的 `lib` 目录在加载器搜索路径上
  （conan 的 `conanrun` 环境已注入）。CI 的 L2 冒烟探针在裸 PATH 下会因此报
  `Error loading shared library`，属 `notes/defects/ci-and-w3.md` 已登记的框架缺陷形态，
  不改变产物可用性；本任务按该条口径做人工补测，见
  `reports/conan-verify-supplement.md`。
- `vpnns` 需要内核支持 user/net/uts/mnt 命名空间与 `mount()`，通常还需特权；本任务只验证其
  CLI 与可加载性，不做命名空间端到端运行。
- 上游没有自动化测试套件；`lwip/test/unit` 的 22 个 Check 用例不参与构建。
