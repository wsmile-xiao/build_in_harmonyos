# lltdscan 0-20180223 — 适配记录

> 分支: feat/lltdscan-0-20180223
> 最后更新: 2026-10-05

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | lltdscan |
| 版本 | 0-20180223（平台任务 #8518 指定，见下方说明） |
| 状态 | built |
| 构建系统 | makefile（无 configure，单 Makefile） |
| 源码 URL | https://codeload.github.com/zed-0xff/lltdscan/tar.gz/258dbb1c7f8672c09a4a578fc17dada524c3eabb |
| sha256 | 678b4813d8ad0d33059797ce16614e8065bcd6ecd7658221967a8aee866f4108 |
| 大小 | 6209 字节 |
| 上游 commit | 258dbb1c7f8672c09a4a578fc17dada524c3eabb（2013-02-04） |
| 依赖 | libpcap/1.10.6、libnet/1.2 |
| 包类型 | application（命令行二层抓包工具，R38: 软件级 commands.json 已声明） |
| 许可证 | Unlicense（上游 README 声明 "Public Domain"） |

### 关于版本号 `0-20180223`

上游 zed-0xff/lltdscan **没有任何 tag 或 release**：GitHub API 列出的全部
tag 为空，提交历史只有 7 条且止于 2013-02-04 的
`258dbb1c7f86`（"Merge pull request #2 from grawity/source-addr"）。
Arch 的 AUR 包因此只能叫 `lltdscan-git`。

所以 `0-20180223` 是**赛事平台任务 #8518 指定的版本号**，不是上游发布号。
配方把源码 URL 固定到上游 master HEAD 的 **commit SHA**（而非会漂移的
`heads/master`），保证任何人重跑都拿到同一份字节。

取证记录：
- `codeload.github.com/.../tar.gz/258dbb1c7f86...` → HTTP 200，6209 字节，
  sha256 `678b4813…108`
- `github.com/zed-0xff/lltdscan/archive/258dbb1c7f86....tar.gz` → HTTP 200，
  6209 字节，sha256 同为 `678b4813…108`（两条官方路径字节一致）
- 未使用任何镜像站（gh-proxy 等一律未走）
- 试过的 tag 形式 `v0.20180223` / `0.20180223` / `v0-20180223` 全部 HTTP 404，
  印证「上游无 tag」

#### 一个容易踩的坑：commit-SHA 归档 ≠ master 归档（sha256 不同）

`refs/heads/master` 归档是 6206 字节、sha256 `6aafc7a3…87b`，
与上面 commit-SHA 归档的 6209 字节 / `678b4813…108` **不同**。
原因是 tar 里的根目录名不同：前者叫 `lltdscan-master/`，后者叫
`lltdscan-<完整40位sha>/`，名字长 34 字符 → tar 头部差 3 字节。

逐文件 sha256 对比确认**内容完全相同**（两个归档的 6 个文件哈希一一相同），
所以这只是归档信封不同，不是内容漂移。首次 `conan create` 时正是拿
master 归档的哈希去校验 commit-SHA 归档，被 Conan 拦下
（`sha256 hash failed`），已改为 commit-SHA 归档的真实哈希。

教训：写 conandata.yml 时，**校验值必须与 URL 里写的那个 URL 对应**，
不要拿「另一个等价归档」的哈希填进去。

## 二、上游测试套件审计（hmbs 机器证据门禁）
审计对象: 上述 6209 字节官方归档（sha256 见上）

- 全树仅 6 个文件: `Makefile` / `README` / `lltdscan.c` / `lltd.c` /
  `lltdscan.8` / `.gitignore`
- 无 `tests/`、`test/`、`spec/`、`t/` 目录；无 `TEST(`/`TEST_F`（gtest）、
  无 `def test_`（pytest）
- Makefile 只定义 `all` / `lltdscan` / `clean` / `doc` / `install` / `dist`
  六个目标，**没有 `check` / `test` / `TESTS` / `check_PROGRAMS`**；
  `make check` → `No rule to make target 'check'`
- README 的 EXAMPLES 段是**手工使用示例**（截图式输出），需要网卡进混杂模式
  且对端运行 LLTD responder，CI 不可复现

结论: 如实声明 `upstream_tests_exist: false` + 非空 `upstream_test_audit`，
不虚构测试数字。功能验证由 test_package 真实执行 lltdscan 二进制完成。

## 三、补丁清单

**无补丁。**

与 cdpr/2.4 不同，lltdscan 的 Makefile 链接行本来就走变量：

```make
lltdscan: lltdscan.c lltd.c
	$(CC) $(CFLAGS2) $(LDFLAGS2) -o lltdscan lltdscan.c -lnet -lpcap -lrt $(EXTRA_LIBS)
```

`CC=gcc` 只是 Makefile 顶部的**默认值**，命令行 `make CC=<clang>` 即可覆盖，
所以 cdpr 那份 `0001-makefile-use-cc-variable.patch` 在这里**不需要**。
不为了「有补丁」而造补丁。

## 四、配方要点（conanfile.py）
- 真正的适配只有一处：CFLAGS2/LDFLAGS2 硬编码了
  `/usr/local/include`、`/usr/local/include/libnet-1.1`、`/usr/include/pcap`、
  `/opt/csw/lib` 等路径（arping/Solaris 遗留）。
  用 `make CC=... "CFLAGS2=..." "LDFLAGS2=..."` 在命令行传同名变量整体覆盖
  （Make 命令行变量优先级高于 Makefile 内赋值），这是 dhcpdump/1.10 与
  cdpr/2.4 的同一手法，**不需要改源码**
- `-I/-L` 从 `self.dependencies["libpcap"/"libnet"].cpp_info` 取（R33：不裸用
  `${CC}` 之类未定义 shell 变量）
- 编译器从 `self.conf.get("tools.build:compiler_executables")` 取
- 平台守卫 `self.settings.os in ("Linux", "OHOS")`（R32）
- `make -j1`（E074：HMDFS jobserver FIFO EPERM）
- package_type=application，`cpp_info.bindirs=["bin"]`，`cpp_info.libs=[]`（R38）
- 一并打包 `lltdscan.8` man page 到 `share/man/man8/`（dhcpdump/1.10 先例）
- build() 不调 `make check`（上游无该目标），MANIFEST 中
  `upstream_test_in_build: false` 如实声明

## 五、验证记录
- 源码：两条官方路径 HTTP 200、6209 字节、sha256 一致（见 §1）
- 依赖：`conan download "libpcap/1.10.6" -r=ohpcd --only-recipe` →
  revision `e4d43bf9a29fdaabd60dee919243c781`；
  `conan download "libnet/1.2" -r=ohpcd --only-recipe` →
  revision `38fc86f3833700bc1a5f4d2493ed7cac`；两者 armv8/Release 二进制均可取到
- 交叉编译：`/opt/lpk-fixed/clang`（target `aarch64-unknown-linux-ohos`），
  `make -n` 确认生效命令为 clang 且 `-I/-L` 指向 Conan 依赖目录；
  实编译 0 error，7 个 warning 全是 `-Wpointer-sign` / `-Wformat` /
  `-Wdeprecated-declarations`（上游 2009-2013 年代码对 `u_char*` 与 `char*`
  混用的老问题，与 OHOS 无关，未改）
- 产物：`ELF 64-bit LSB pie executable, ARM aarch64`
- 运行：test_package 5 例 / 19 断言全通过（见 §六）

## 六、功能验证覆盖范围

lltdscan 不带 `-i` 会 `pcap_lookupdev()` → libnet 构造广播帧 →
`pcap_dispatch()` 阻塞到超时。**test 里绝不能裸跑 `lltdscan`**：要混杂模式、
root 权限、真实网卡和对端 LLTD responder。

所以 test.sh 只覆盖**在打开任何 socket 之前就返回**的确定性路径，
这些路径真实执行二进制、真实走 getopt 解析与参数校验：

| 用例 | 断言数 | 说明 |
|------|--------|------|
| `-h` | 8 | exit 0 + 输出非空 + 横幅含程序名 + 用法横幅 5 项（选项全序列/timeout/-u/-v/尾随 MAC） |
| `-Z` | 2 | 未知选项被拒，`unrecognized option: Z` + exit 1 |
| `-t`（缺参数） | 2 | `option requires an argument: t` + exit 1 |
| `aa:bb` | 2 | 畸形 MAC 被拒，`Invalid MAC-address: 'aa:bb'` + exit 1 |
| 两个尾随 MAC | 6 | argc>1 分支打印完整用法横幅 + exit 1 |

合计 20 断言 / 5 用例，全部实测通过。

写测试时踩到的一个上游细节：主函数在 getopt 之后做了
`argc -= optind; argv += optind;`，所以在「两个尾随 MAC」这条路径上
`argv[0]` 已经被前移成第一个 MAC 字符串，`usage()` 打出的是
`usage: aa:bb:cc:dd:ee:ff [-i iface] ...` 而不是 `usage: .../lltdscan ...`。
因此公共断言只匹配选项全序列（各路径一致），「横幅含程序名」单独放在
`-h` 用例里断言（那条路径 argv 未前移）。

## 七、遗留问题与风险
- **无已知编译阻塞**
- **不做真实抓包验证**：需混杂模式 + root + 对端 LLTD responder，CI 不可复现。
  若需端到端证据，只能在真机上对着开着 "Link-Layer Topology Discovery
  Responder" 的 Windows 主机跑，属人工步骤
- `-Wpointer-sign` 等 7 个 warning 保留未修：属上游 2009-2013 年代码风格
  （`u_char*` 与 `char*` 混用），修改会偏离「适配」范围变成「重构」，
  且无功能影响。如需清理应另开任务
- 版本号 `0-20180223` 与上游无对应 release，提交评审时需知会评审者：
  以 notes.md §1 + conandata.yml 注释为准