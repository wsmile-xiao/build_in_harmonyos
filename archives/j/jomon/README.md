# jomon

终端 TCP 连接监视器：以 ncurses TUI 按连接展示 TCP 会话状态、吞吐与统计信息，
支持 tcpdump 语法的过滤器、BPF 反汇编输出，以及从 tcpdump 抓包文件离线分析。

- 上游仓库：<https://github.com/jo-lund/jomon>
- 许可：MIT
- 语言：C（`-std=gnu11`）
- 依赖：ncurses（必须）；GeoIP（可选，本适配关闭）

## 构建系统

上游使用**自制 configure（bash，非 autoconf 生成）+ Makefile**：

- `./configure [--disable-geoip] [--set-geoip-path <path>] [--prefix <path>]`
  依次执行 check_gcc / check_ncurses / check_geoip / check_re2c / check_python3 /
  check_missing，并生成 `config.h` 与 `config.mk`。
- `make` 产出 `bin/jomon`；`make test` 用 libcheck 运行 `tests/` 下的单元套件。
- 源码包（tarball）内没有 `.git`，`configure` 原用 `git describe` 取版本号。

## HarmonyOS PC（OHOS aarch64）适配

补丁（3 个，均为 portability 类型）：

| 补丁 | 修改内容 |
|------|----------|
| `0.6.4/patches/0002-configure.patch` | 能力探测带上 `$CFLAGS/$CPPFLAGS/$LDFLAGS`；支持 `JOMON_VERSION` 注入；探测宽字符 ncurses |
| `0.6.4/patches/0001-Makefile.patch` | `LIBS := -lncursesw -lrt $(LDFLAGS)`（链接行不再丢弃 LDFLAGS） |
| `0.6.4/patches/0003-portability.h.patch` | 非 glibc libc（OHOS musl）无 GNU `qsort_r`，在 `qsort` 之上提供 shim |

| 问题 | 现象 | 处理 |
|------|------|------|
| 探测不带编译参数 | `configure` 的探测只调裸 `$CC`，交叉编译时看不到 conan 依赖的头文件与库路径，`check_ncurses` 失败退出 | 探测命令带上 `$CFLAGS $CPPFLAGS ... $LDFLAGS` |
| 版本号 | tarball 无 `.git`，`git describe` 失败导致 `VERSION` 为空 | 支持 `JOMON_VERSION` 注入，配方传 `self.version` |
| ncurses 库名 | conan 的 ncurses 包只提供宽字符库 `libncursesw`，上游探测/链接的 `-lncurses` 找不到 | 探测与 `LIBS` 改为 `-lncursesw` |
| 链接行丢弃 `LDFLAGS` | Makefile 链接命令未使用 `$(LDFLAGS)`，依赖库搜索路径丢失 | `LIBS := -lncursesw -lrt $(LDFLAGS)` |
| 无 GNU install | OHOS 无 `install` 命令，上游 `make install` 不可用 | 配方用 `conan copy` 直接落盘 `bin/jomon` |
| 无 GNU `qsort_r` | OHOS musl 无该符号，上游 `QSORT()` 宏调用编译/链接失败 | `portability.h` 加 shim（`#ifndef __GLIBC__`，单线程语义） |

无需补丁的项：OHOS libc 无 `obstack`/`strlcpy`，`configure` 探测失败后自动编入
`compat/obstack.c`、`compat/strlcpy.c`。

### 配方要点

- `tool_requires("re2c/4.3.1")`：`configure` 用 `command -v re2c` 检查，
  `re2c` 生成 `bpf/bpf_lexer.c`、`bpf/pcap_lexer.c`。
- `python3`（构建环境自带）执行 `scripts/genprotocols.py` 生成
  `decoder/decoder.h`、`decoder/register.h`。
- 使用 `AutotoolsToolchain` 注入编译环境：**不能用 `make CFLAGS=...` 覆盖**，
  命令行赋值会让 Makefile 内 `CFLAGS += -std=gnu11 -fwrapv ...` 失效。
- ncurses 强制静态（`self.options["ncurses"].shared = False`），避免与系统同名库冲突。
- 产物只有 CLI 可执行文件，因此软件级目录提供 `commands.json`（R38）。

## 使用

```bash
conan install --requires=jomon/0.6.4 -r=ohpcd
jomon --help                    # 查看全部选项
jomon -i eth0                   # 监视指定接口
jomon -ddd -f "tcp or icmp"     # 编译 tcpdump 语法过滤器并反汇编（离线，无需 root）
jomon -d -f "udp"               # 反汇编为 BPF 汇编
jomon -r capture.pcap           # 离线读取 tcpdump 抓包文件
```

> 过滤器仅支持 tcpdump 语法子集（`ip`/`tcp`/`udp`/`arp`/`icmp` 等）；`port`/`host`/`ether`
> 属上游未实现范围（jomon 自带手写过滤器编译器，不依赖 libpcap）。
>
> 捕获实时流量需要相应权限（`CAP_NET_RAW`/root）；`-d/-dd/-ddd` 的过滤器反汇编
> 与 `-r` 离线分析不需要。
