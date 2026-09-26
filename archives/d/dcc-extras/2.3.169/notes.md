# dcc-extras 2.3.169 适配笔记

## 身份与版本

| 项 | 值 |
|---|---|
| 请求名 / 源包名 | `dcc-extras` / DCC（Distributed Checksum Clearinghouse） |
| 上游工程 | <https://www.dcc-servers.net/dcc/>（Rhyolite Software） |
| 上游真实版本 | **2.3.169**（2024-03-22；`CHANGES:5` = `2.3.169`，`configure:404` `ac_cv_DCC_VERSION=2.3.169`） |
| 源码 | `https://www.dcc-servers.net/dcc/source/dcc.tar.Z`，sha256 `3447e655…b7bf6`，1 534 973 B |
| 语言（R47） | `c`（`ohc-run.py lang-preflight` → detected=c） |
| 构建系统 | autotools（autoconf-2.13 风格 `configure` + GNU make） |

`dcc-extras` 不是任何发行版的独立二进制包名；它对应同一 tarball 的辅助/测试工具面
（cdcc、ck2ip、dccd、dccifd、dccproc、dccsight、dbclean、dblist、dump-clients、
dns-helper、wlist、cgi-bin、`dccifd/dccif-test`）。上游 `make` 默认即构建上述全部
组件，因此本配方交付上游默认全集。

## 编译环境

- 平台：HarmonyOS PC / aarch64（`uname` → `HarmonyOS … aarch64`）
- 编译器：clang 15.0.4（OHOS SDK `aarch64-linux-ohos`，sysroot 为 musl）
- 日期：2026-09-26；状态：`built`（`conan create` + `conan-verify` + `finish` 全绿，
  停在 push/PR 前等待确认）

## 安装/配置步骤（上游约定的参数集）

```bash
sh ./configure --disable-sys-inst --bindir=/usr/bin \
    --with-installroot=<stage>          # 等效 DESTDIR（Makefile.inc.in: BINDIR=@installroot@@bindir@）
make -j8
make -C <subdir> install                # 逐组件（见「问题 3」）
```

`--with-installroot` 只影响**安装目标**；运行期路径仍为上游默认
（`DCC_HOMEDIR=/var/dcc`、`DCC_LIBEXECDIR=/var/dcc/libexec`、`DCC_RUNDIR=/var/run/dcc`）。

## 遇到的问题与解决方案

| # | 问题（首个真实错误） | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `make` 立刻中断：`../include/dcc_errlog.h:16:8: error: unknown type name 'u_char'; did you mean 'char'?`（全树 93 个 `.c` 同错） | DCC 假定 BSD 别名 `u_char/u_int*_t/caddr_t` 由 `<sys/socket.h>`、`<netdb.h>` 等传递引入（glibc 成立）。OHOS sysroot 是 **musl**：这些别名只定义在 `<sys/types.h>`，受 `_GNU_SOURCE`/`_BSD_SOURCE` 门控，而 `include/dcc_types.h` 不含该头 → 全部类型不可见（`configure` 的另一处探测因为**自己显式 include 了 `<sys/types.h>`** 反而报 `u_int32_t... yes`，与源码实际不符） | 补 `include/dcc_types.h`：`#include <sys/types.h>`（POSIX 保证存在，对所有平台等价无害；**无平台宏**，R8）。见 `patches/0001-include-dcc_types.h.patch` |
| 2 | `configure` 直接退出：`error: --prefix is not what you think it is.`（rc=1） | 上游 configure 有意拒收 `--prefix`（该项目用 `--homedir` 概念），只认 `--homedir/--bindir/--libexecdir/--mandir/--with-installroot` | 按上游约定传参，不加 `--prefix`；打包用 `--with-installroot`（等效 DESTDIR） |
| 3 | 顶层 `make install` 报 `homedir` 失败但 **rc=0**：`open(.../var/dcc/map): File exists` + `make[1]: *** [Makefile:31: install] Error 69` | 两个问题叠加：**(a)** 顶层 `install` 用 shell `for` 循环递归子目录，最后一个目录成功即 rc=0，掩盖 homedir 失败；**(b)** homedir 的 `fix-map` 调 `cdcc` 建 map，DCC 打开 map 时带 `HAVE_PRIVATE_FILES` 检查（`clntlib/lock_open.c:141` `st_mode & (S_IRGRP\|S_IWGRP\|S_IWOTH\|S_IXOTH)`）要求 0600，而本机 `/storage`（HMDFS/tmpfs）把**任何**文件权限归一化为 `0660` 且 `chmod` 无效 → 检查必然失败 → cdcc 退出 69 → `fix-map` 因 `set -e` 中止 | 逐目录 `make -C <dir> install`（让失败显性化）；安装时**跳过 homedir 的密钥生成**（map/ids 是主机专属随机密钥，不应进入可重定位包），改交付上游静态配置原型到 `res/dcc/` |
| 4 | 上游只发 `dcc.tar.Z`：`conan get()/unzip` 与 toybox `gzip` 均无法解 `.Z`（LZW） | compress(1) LZW 非 gzip；本机无 `uncompress`，`/usr/bin/gzip` 实为 toybox | 配方 `source()` 用 `cmake -E tar xf dcc.tar.Z`（CMake 内置 libarchive 支持 compress），与仓内 `archives/c/cspice/67.0.0.1` 同一做法 |

> 关于问题 3 的实测证据：`python3 -c "os.open(p, O_CREAT|O_EXCL|O_RDWR, 0o600)"` 在
> `/storage/Users/...` 下得到 `0o660`，`chmod(600)` 后仍为 `0o660`；在 `/dev/shm`
> 下为 `0o600`（说明是文件系统而非代码问题）。逐行 trace 定位到 `fix-map:72`
> 的 `cdcc -qh$HD file=$MAP` 探针 + `fix-map:99` 的 `new map` 复建。

## 源码修改

仅 1 个补丁（`patches/0001-include-dcc_types.h.patch`）：

```diff
--- a/include/dcc_types.h
+++ b/include/dcc_types.h
@@ -30,6 +30,7 @@
 #include <netdb.h>
 #include <netinet/in.h>
+#include <sys/types.h>			/* POSIX: u_char/u_int*_t/caddr_t live here */
 #include <sys/param.h>			/* for FreeBSD */
 #include <sys/socket.h>
```

## 依赖

- **强制第三方依赖：无**（`configure` 的全部库探测均为系统库或可选特性）
- 系统库（工具链 sysroot 自带）：libc/musl、libm（`configure:1023` `-lm`）
- 可选且已可消费（ohpcd）：`libmilter/8.18.2`（dccm 用；缺席时上游按设计不构建 dccm）、
  `editline/2.1.0` + `termcap/1.3.1`（cdcc 行编辑；`histedit.h` 缺席时不启用）
- 同源树内静态库：`dcclib/libdcc.a`、`clntlib/libclnt.a`、`thrlib/libthr.a`、`srvrlib/libsrvr.a`

## 验证结果

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-create ...   # 见 reports/（真实日志）
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify dcc-extras 2.3.169
python3 $SKILL_ROOT/scripts/ohc-run.py finish dcc-extras 2.3.169 built
```

- 上游构建：`make -j8` rc=0（20 个 SUBDIR 全绿）
- 安装：15 个组件目录 `make -C <dir> install` 全部 rc=0
- 上游测试：**无自动化测试套件**（R51 三步法清点证据见 `reports/test-report.md`）；
  13 个可执行入口的真实执行矩阵亦在该报告
- `test_package`：C 消费者测试（链接 libdcc 并调用 `dcc_hstrerror`，含 OHOS 专有类型断言）
  + 13 例 shell 套件

## 部署说明（运行期）

- 包内可执行文件的内置路径为上游默认：`DCC_HOMEDIR=/var/dcc`、
  `DCC_LIBEXECDIR=/var/dcc/libexec`、`DCC_RUNDIR=/var/run/dcc`。
  部署时应创建 `/var/dcc` 并把 `libexec/` 复制为其 `libexec/`（或按需调整
  `dcc_conf`），把 `res/dcc/` 的原型复制为 `/var/dcc/` 下的配置。
- `map`/`ids`（含随机 secret 的主机专属文件）不在包内：在**支持 0600 的文件系统**
  上执行包内 `libexec/fix-map`（例如
  `libexec/fix-map -n '' -c bin/cdcc -h /var/dcc -i /var/dcc/ids -m /var/dcc/map -t /var/dcc/map.txt`）
  即可生成。HMDFS 等把权限归一化为 0660 的文件系统上 DCC 会按设计拒绝使用该 map。

## 交付物

| 路径 | 说明 |
|---|---|
| `bin/` | cdcc、dccproc、dccif-test |
| `libexec/` | dccd、dccifd、dbclean、dblist、dccsight、ck2ip、dump-clients、dns-helper、wlist、check_ip_range、fix-map + 运行脚本 |
| `cgi-bin/` | Perl CGI |
| `include/` + `lib/` | DCC 公共头文件 + libdcc.a/libclnt.a |
| `res/dcc/` | 上游静态配置原型 |
| `licenses/LICENSE` | 上游许可证 |

## 注意事项

- 上游 `configure` **不能**传 `--prefix`。
- `make extras` 不是顶层目标；`dccif-test` 由 `dccifd` 子目录随 `make` 默认构建
  （OpenMandriva spec 的 `# make extras` 即 `make -C dccifd/dccif-test`）。
- `dccm` 未构建：libmilter 缺席，上游文档明确 dccm 为可选（`INSTALL.html.in:148`）。
- 顶层 `make install` 的返回码不可信（for 循环掩盖子目录失败）——本配方改逐目录安装。
---

**编译结束**: 2026-09-26 08:39
**最终状态**: built
