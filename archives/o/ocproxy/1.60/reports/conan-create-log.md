# ocproxy 1.60 真机 conan create 日志（证据）

- 设备：HarmonyOS PC aarch64（HongMeng Kernel 1.12.0），`HOME=/storage/Users/currentUser`
- 独立 `CONAN_HOME=/storage/Users/currentUser/work/psj/ch-ocproxy`（conan 2.29.1）
- profile：`ohos-aarch64`（`os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.version=15 compiler.cppstd=17 build_type=Release`）
- 命令：`conan create archives/o/ocproxy/1.60 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
- 时间：2026-09-20 01:06:35 → 01:11:24（本地缓存 ch-ocproxy）
- **结果：`CREATE_EXIT:0`，包 id `6c61b811dee32ee923502180c65131bd5a2ee7df`，recipe revision `28a15b4c5522d914f409067c08c77287`**
- 上游测试：`0/0`（上游无可运行测试入口，见 `upstream-test-inventory.md`）
- 消费者（鸿蒙特有）测试：**`TOTAL=17 PASS=17 FAIL=0`**

## 关键构建步骤（逐字摘取）

```text
Apply patch (portability): Add -V/--version and -h/--help to ocproxy ...
Apply patch (portability): Port vpnns to the OHOS libc: replace the GNU-only get_current_dir_name() ...
autoreconf --force --install --verbose
autoreconf: running: .../ch-ocproxy/p/autom.../bin/aclocal --force
autoreconf: running: .../ch-ocproxy/p/autom.../bin/automake --add-missing --copy --force-missing
RUN: .../b/configure --build=aarch64-linux-ohos --host=aarch64-linux-ohos
checking build system type... aarch64-unknown-linux-ohos
checking host system type... aarch64-unknown-linux-ohos
checking for aarch64-linux-ohos-gcc... .../ohos-sdk@26.0.0.18/native/llvm/bin/clang
make -j1  ...  CCLD     ocproxy
make -j1  ...  CCLD     vpnns
make install -j1
ocproxy/1.60: Package '6c61b811dee32ee923502180c65131bd5a2ee7df' created
```

依赖：`libevent/2.1.13`（Cache，来自 ohpcd 制品仓）、`zlib/1.3.1.1`（test req，Cache）、`automake/1.18`（`tool_requires`，Cache）。源码 sha256 `a7367647f07df33869e2f79da66b6f104f6495ae806b12a8b8d9ca82fb7899ac` 校验通过（与 conandata/manifest 一致，且与 Debian 签名 orig tarball 逐字节相同）。

## test_package 输出（打包产物，真机 OHOS 运行时）

```text
== package layout ==
  [PASS] ocproxy installed and executable
  [PASS] vpnns installed and executable
== failure modes ==
  [PASS] missing VPNFD fails closed :: rc=1 out='VPNFD is not set, aborting'
  [PASS] non-numeric VPNFD fails closed :: rc=1 out="invalid integer: 'not-a-number'"
== live proxy behaviour ==
  [PASS] -D SOCKS5 listener accepts connections
  [PASS] -L port-forward listener accepts connections
  [PASS] SOCKS5 no-auth negotiation answered :: 0500
  [PASS] SOCKS5 CONNECT accepted for tunnel delivery
  [PASS] SOCKS5 request produced tunnel traffic :: bytes_read_from_tunnel=227
  [PASS] malformed -D fails closed
  [PASS] truncated -L fails closed
== version and help switches ==
  [PASS] ocproxy --version works without a tunnel :: 'ocproxy 1.60 - user-level SOCKS and port forwarding proxy'
  [PASS] ocproxy -V short form works :: 'ocproxy 1.60 ...'
  [PASS] ocproxy --help lists the tunnel options
== vpnns ==
  [PASS] vpnns -h prints usage and exits 1
  [PASS] vpnns -v prints version and exits 0 :: 'This program is part of the ocproxy 1.60 package.'
  [PASS] vpnns without a command fails closed :: 'no command given'
TOTAL=17 PASS=17 FAIL=0
```

`bytes_read_from_tunnel=227` 证明 SOCKS5 `CONNECT` 请求被 lwIP 协议栈接受并生成真实隧道报文写入 `VPNFD`（用 socketpair 观察；HMDFS 上 pipe 写端 select 不可读）。

## 真机环境注记（不改配方，仅本机）

1. **源码下载**：`github.com` 拉 tarball 偶发 `ConnectTimeout`（conan 的 30s 连接超时）。本次 runner 内 conan 自身重试后成功下载；配方 `conandata.yml` 保持单值 `url`（CI 镜像注入只匹配单值 `url:`，与已合入 `1.6` 一致，CI worker 侧不受该抖动影响）。
2. **`automake/1.18` 的 aclocal/automake 在本机可执行性**：该包的 `bin/.aclocal-real`、`bin/.automake-real`（含 `-1.18-real`）shebang 硬编码 `#!/data/service/hnp/bin/perl`。`/data/service/hnp/bin/perl` 是 **CI worker** 才有的路径，真机上不存在（真机 perl 在 `~/.harmonybrew/bin/perl`），因此真机首次 `autoreconf` 报 `aclocal failed with exit status: 126`。这是 `agent.md` §2.1 drogon 记录的同族「本机工具路径差异」。**配方未做任何修改**：只在我独立的 `ch-ocproxy` 缓存内把这 4 个脚本的 shebang 就地改指真机 `~/.harmonybrew/bin/perl`（与他人缓存/共享 `~/.conan2`/制品仓完全隔离，可随时 `conan remove automake/* -c` 复原），随后 `autoreconf` 正常产出 `configure`。CI worker 上 `/data/service/hnp/bin/perl` 本就存在，无需该步。
