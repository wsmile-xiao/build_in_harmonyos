# mstpd 0.2.0 适配笔记

## 编译环境

- 构建系统：Autotools（configure.ac + Makefile.am + autogen.sh；官方 tag 归档内**不含**生成好的 configure，配方负责自举）
- 编译日期：2026-09-26
- 编译器：clang（OHOS NDK sysroot，/data/service/hnp/bin）
- 构建主机：B 机（HarmonyOS aarch64，HongMeng Kernel 1.12.0，8 核 / 31G）
- CONAN_HOME：~/tmp/ch/home-mstpd（独立于其它任务）
- 取源：https://github.com/mstpd/mstpd/archive/refs/tags/0.2.0.tar.gz
  - sha256 自算：37cbc03ab14763a2d477d2230508ab98c2acec43fa869b985c264d44e125c386（117075 字节）
  - 上游 release 0.2.0 未附带任何发布资产，tag 名不带 v 前缀，GitHub 的 tag 归档即官方唯一机器可读源（R39/PF7）
  - 说明：Debian 池里 .orig 的指纹与本枚不相等属正常（.orig 是 Debian 重打包形态），配方不引用池址

## 编译步骤（配方实际执行顺序）

1. tool_requires：automake/1.18（提供 aclocal/automake）、libtool/2.5.4（提供 libtoolize，因为 configure.ac 调 LT_INIT）。
   **不**声明 autoconf/m4：SDK 已在 /data/service/hnp/bin 提供 autoconf 2.72 / autom4te / m4 / perl。
2. _bootstrap_env()：把 SED/AUTOCONF/AUTOHEADER/AUTOM4TE/M4 导出为 command -v 实测路径；TMPDIR 建在 build_folder 内；
   CONFIG_SHELL/SHELL 指向实测 bash；按 glob 发现 SDK 的 pkg.m4 目录并前置进 ACLOCAL_PATH。
3. autoreconf --install --force（等价上游 autogen.sh 的 autoreconf -W portability -visf）
4. configure：--build/--host 显式钉成 aarch64-unknown-linux-gnu；--disable-install-ifupdown-scripts；CFLAGS 追加 -D__MUSL__
5. make -j1 → make install（conan 的 prefix 即包目录，不写系统目录）

## 适配点（症状 / 根因 / 最小复现 / 已试过的失败方案 / 最终方案 / 适用边界）

### 1. sockaddr_storage 重复定义（命中 E091）

- 症状：error: redefinition of 'sockaddr_storage'，第一处 sys/socket.h:377，第二处 linux/socket.h:23。
- 根因：OHOS NDK sysroot 的 sys/socket.h 把 struct sockaddr_storage 包在 #ifndef __MUSL__ 里，而 linux/socket.h
  无条件定义同一个结构体。mstpd 的 libnetlink.c 第 19 行含 sys/socket.h，又经 libnetlink.h 第 6 行含
  linux/netlink.h，两路必撞。
- 最小复现（本机实拍）：一个只含 #include <sys/socket.h> 与 #include <linux/netlink.h> 的 .c 文件用 clang 语法检查即报；
  本包 test_package/test_probe.c 不加 -D__MUSL__ 的编译同样报（对照臂见运行面小节）。
- 已试过的失败方案：调 include 顺序（两文件都是无条件展开路径，无效）；改上游源码补 extern（改生成物之外的上游代码，面更大且违背最少改动）。
- 最终方案：tc.extra_cflags 追加 -D__MUSL__，让 sysroot 自带的守卫生效，不改上游一行源码。
  与已合入的 acpid/2.0.34 同处理（conanfile.py 的 CFLAGS 段），仓内 77 处使用这一标记。
- 与既有条目的差别（要点，供判档）：E091 原文推荐的是源码层 define-guard——在 include linux/netlink.h 前
  用平台专有宏把 sockaddr_storage 改名。该写法今天会被 PF5 平台宏闸拦（patches 与 conanfile 新增行的平台宏注入同拦），而 -D__MUSL__ 走的是 sysroot 自己的守卫分支，二者是同一错误的两条不同层次解法。
- 适用边界：任何同时包含 linux/*.h 与 sys/socket.h 的网络/netlink 类包。

### 2. 无 configure 的 autotools 自举（命中 E521，旁及 E116 / E049）

- 症状：自举阶段 automake 报 required file ./ltmain.sh not found；或直接 automake --version 报
  No such file or directory（解释器缺失），libtool --version 报家目录 usr local 下的 sed inaccessible or not found。
- 根因：最小化 OHOS 镜像里家目录工具目录中的 automake/aclocal/libtool/libtoolize 是带绝对路径 shebang 与内嵌 SED 路径的
  安装件，被引用的解释器/ sed 实际不存在；SED 未设时 libtoolize 的 aux 目录启发式会向上走一层，把 ltmain.sh 放错位置，
  automake 随后致命退出（E521 原文即此，PR !5330）。
- 最小复现（本机实拍）：autoconf --version 正常返回 2.72，但 automake --version 立刻报 interpreter 缺失；
  ls ~/usr/local/bin/perl 返回 No such file or directory，而 head -2 ~/usr/local/bin/automake 的 shebang 正指向它。
- 已试过的失败方案：直接用镜像内的 automake/libtoolize（同机必挂）；把 autoconf/2.72 与 m4 也 tool_requires
  （accel-config 记录：会连带拉进 OHOS 版 perl，其 XS 模块与 SDK perl 解释器冲突，报 Perl_my_cxt_init 符号找不到）。
- 最终方案：只声明 automake/1.18 + libtool/2.5.4 由 conan buildenv 提供工具与 ACLOCAL_PATH/_lt_pkgdatadir，
  再按 E521 显式导出 SED/AUTOCONF/AUTOHEADER/AUTOM4TE 的实测路径。
- 适用边界：GitHub tag 归档不带生成 configure 的 autotools 包。

### 3. PKG_PROG_PKG_CONFIG 的 pkg.m4 不在惯例目录

- 症状：autoreconf 报宏 PKG_PROG_PKG_CONFIG 在 aclocal 搜索路径内找不到。
- 根因：本机/CI 的 pkg-config 是 SDK 件，其 aclocal 目录实为
  /data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal，而惯例的 /data/service/hnp/share/aclocal 不存在。
- 最小复现（本机实拍）：shutil.which(pkg-config) 得 /data/service/hnp/bin/pkg-config；对其上级目录做两种拼法，
  只有 pkg-config.org/pkg-config_*/share/aclocal 命中且内含 pkg.m4。
- 已试过的失败方案：只拼 <root>/share/aclocal 一种候选（实测目录不存在，等价于没做发现）。
- 最终方案：两种布局都 glob，命中项前置进 ACLOCAL_PATH，另把 tool 图内 libtool 的 share/aclocal 追加进去。
- 适用边界：用到 pkg.m4 / autoconf-archive 一类"宏在第三方件里"的 autotools 包。

### 4. 主机三元组与安装落点

- 症状：config.guess 推不出主机类型（uname -s 返回 HarmonyOS，不在其识别表内）；上游默认落点含
  usr local 前缀与 /etc、/var 下的系统路径（SCT 行提示"Makefile/configure 内 /usr/local 出现 1 处"）。
- 根因：归档不 ship config.guess/config.sub（实测树内无这些辅助件，靠 autoreconf --install 从工具包复制）；
  Makefile.am 的 install-exec-hook 会往 /etc/network 下建 ifupdown 符号链接。
- 最小复现：解包后 ls configure config.guess 全部不存在；grep -n network Makefile.am 命中 if-pre-up.d 链接行。
- 已试过的失败方案：把 --host 留空让 configure 自猜（落到 config.guess 未识别）；留着 ifupdown 开关（装到包外的 /etc 下）。
- 最终方案：--build 与 --host 显式钉成同一 gnu 三元组（保持 native 语义，configure 的探测真跑而非退化成交叉默认值）；
  前缀交给 conan 的 package folder；显式 --disable-install-ifupdown-scripts。
- 适用边界：OHOS 上所有 autotools 包（sysname 与 gnu 表不匹配是平台级事实）。

### 5. ethtool_cmd_speed 内核内联缺失导致链接期未定义符号

- 症状：编译期 `netif_utils.c:120` 报 `warning: call to undeclared function 'ethtool_cmd_speed'
  (-Wimplicit-function-declaration)`；链接期 `ld.lld: error: undefined symbol: ethtool_cmd_speed`
  （referenced by netif_utils.c，函数 ethtool_get_speed_duplex），`make` 以 Error 1 中断。
- 根因：`ethtool_cmd_speed()` 在 Linux uapi 头里是 `static inline`（不是导出符号），只有头提供该内联时调用点
  才在编译期被就地展开。OHOS NDK sysroot 的 `linux/ethtool.h` 定义了 `struct ethtool_cmd`（含 `__u16 speed` /
  `__u16 speed_hi`），却整段省略了这个内联访问器（实测该头 `grep -c ethtool_cmd_speed` = 0）。于是调用点退化成
  隐式声明的外部函数：编译只给 warning，链接期找不到符号。
- 最小复现（本机实拍）：sysroot 头 `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include/linux/ethtool.h`
  内 `ethtool_cmd_speed` 出现 0 次，而 `struct ethtool_cmd` 的 `speed`/`speed_hi` 两枚字段俱在；调用点唯一在
  `netif_utils.c:120`（同函数 `:111 struct ethtool_cmd ecmd;`、`:115 ioctl(netsock, SIOCETHTOOL, &ifr)`）。
- 为什么不用别的解法：① `-Wl,--unresolved-symbols=ignore-all` 只把 undefined 掩盖掉，运行时真调用即崩溃，属缩分母；
  ② 往上游 `.c` 塞 `#define ethtool_cmd_speed(x) ...` 宏会污染该翻译单元所有同名调用、且违背最少改动；
  ③ `--disable-*` / `-DHAVE_ETHTOOL=0` 会把链路速率查询整块缩掉——这是上游真实调用面（ethtool_get_speed_duplex
  被端口速率读取用到），关掉等于砍功能。
- 最终方案：上游补丁 `patches/0001-netif-utils-ethtool-speed-ohos.patch`，把该调用点按内核 ABI 逐字展开成
  `(ecmd.speed | (ecmd.speed_hi << 16))`，只替换这一行表达式，不改语义、不动其它调用面；conandata.yml 的 patches 段登记，
  `build()` 顶部既有 `apply_conandata_patches(self)` 走标准路径施加。
- 语义等价论证：内核 `include/uapi/linux/ethtool.h` 的该内联实现逐字为
  `return ecmd->speed | (ecmd->speed_hi << 16);`（speed 为低 16 位、speed_hi 为高 16 位，合成 32 位速率 Mbps）。
  本补丁对该表达式只是把 `ecmd->` 换成 `ecmd.`（形参是指针、实参是栈上结构体），运算完全同源；本 sysroot 里
  `struct ethtool_cmd` 的 speed/speed_hi 偏移与宽度与内核一致，故读到的值与原内联逐位相同。
- 与先例的关系：同机制已合入两枚——`archives/n/ntopng/6.6/patches/0003-utils.cpp-ethtool-speed-ohos.patch`
  （把 `ethtool_cmd_speed(&edata)` 换成 `(edata.speed | (edata.speed_hi << 16))`，披露见其 notes.md:140）与
  `archives/l/libstatgrab/0.92.1/patches/0001-src-libstatgrab-network_stats.c.patch`（按 speed_hi/speed 直接计算，
  不依赖该内联是否声明）。复用前先在本包实物 grep 三处锚点：`^#include <linux/ethtool.h>`（netif_utils.c:37 命中）、
  `struct ethtool_cmd`（:111 命中）、`speed_hi`（sysroot 头命中）——锚点皆中才照搬形状，形参名按本包上游实物用 `ecmd` 非 `edata`。
- 适用边界：任何在 OHOS sysroot 下调用 `ethtool_cmd_speed()`/`ethtool_cmd_speed_set()` 等内核 `static inline`
  访问器的网络工具包（头提供结构体却不提供内联）。

### 6. scandir 比较器 versionsort 在 OHOS 不存在 ⇒ 回退 POSIX alphasort

- 症状（第二棒遗留首错，本轮实拍）：`ctl_main.c:452:57: error: use of undeclared identifier 'versionsort'`
  与 `ctl_main.c:1171:58:` 同一错，`make[1]: *** [Makefile:724: mstpctl-ctl_main.o] Error 1`，
  配方 `build()` line 209 抛出。
- 根因（本包一手三档证据，不是转抄先例）：OHOS NDK sysroot 的 `<dirent.h>` **根本不提供** GNU 的 versionsort(3)。
  ①对整棵 sysroot include 树 grep `versionsort` 命中 **0** 次；②`<dirent.h>` 的
  `#if defined(_GNU_SOURCE) || defined(_BSD_SOURCE)`（40-53 行）与 `_LARGEFILE64_SOURCE || _GNU_SOURCE`
  （55-64 行）两块里只补了 `getdents()`、`DT_*`、`*64` 别名，**没有任何 versionsort 声明**
  ⇒ `-D_GNU_SOURCE` 不可能把它变出来；③本文件的**真实编译行本来就带 `-D_GNU_SOURCE`**
  （reports/conan-create.log:272，整行 `-DHAVE_CONFIG_H -I. … -D_REENTRANT -D__LINUX__ -I. -D_GNU_SOURCE
  -DMSTPD_PID_FILE=… -O3 -D__MUSL__ …`），clang 仍报 undeclared identifier；把同一组旗标喂给一个
  `scandir(...,versionsort)` 最小 TU ⇒ rc=1 同错，喂 `alphasort` ⇒ rc=0 且 stderr 空（0 字节）。
- 调用面只有两处，且都只做"列举"：`get_bridge_list()`（:452）枚举 SYSFS_CLASS_NET 下的桥接口，
  `get_port_list()`（:1171）枚举某桥 `brif` 下的端口；**条目集合由过滤器决定**（`isbridge` /
  `not_dot_dotdot`），比较器只决定**列出次序** ⇒ 换比较器不改变可见性，只改变观感。
- 最终方案：补丁 `patches/0002-ctl-main-versionsort-alphasort-ohos.patch` 在这两处加
  `#ifdef __OHOS__` 分支把比较器换成 POSIX `alphasort(3)`（sysroot 声明的
  `int alphasort(const struct dirent **, const struct dirent **)` 与 scandir 第四参数逐字一致），
  `#else` 分支保留上游 versionsort 不动；`__OHOS__` 由 SDK clang 预定义（同旗标 `-dM -E` 实拍
  `#define __OHOS__ 1`）。形状取自仓内已合入先例 buildtorrent/0.9.1（其
  `_patch_versionsort_fallback()` docstring 记的正是"`-D_GNU_SOURCE` 加了仍报 undeclared"）、
  alsa-lib/1.2.12、alsa-utils/1.2.14；本包按上游实物两处调用面逐字改，形参名沿用上游
  （`namelist` / `isbridge` / `not_dot_dotdot`），不照抄别包变量名。
- **必须披露的行为改动**（是一次语义回退，不是"上游不支持"）：OHOS 上 `mstpctl showbridge` 与
  `showport` 的**列出次序**由"内嵌版本号序（versionsort）"降级为"字典序（alphasort）"；
  条目集合、字段、退出码、可用性均不变。不禁用任何功能面、不跳过任何测试、不改任何生成物。
- 为什么不用别的解法：① `-D_GNU_SOURCE` 已在本包一手证不足（上面③），加它只会多出重定义警告；
  ② `#if 0` 掉调用面、或把 scandir 第四参数改成 `NULL`＝把"排序"这块功能缩掉，属缩分母；
  ③ 给 configure 加"探测 versionsort"的假探测＝把编译期事实伪装成探测期事实，且上游无对应宏
  （configure.ac 只有 `AC_CHECK_FUNCS(clock_gettime)`，改了也没有消费者）。
- 补丁自证（双重）：toybox `patch -p1 --dry-run` rc=0 且目标文件未被改动；真 apply rc=0，
  产物 sha256 与生成器期望值逐字相等（`35434a5040845c8d…`）；`patch -p1 -R` 反向回到原始
  sha256（`2bad2cf3e3e7e655…`）；再用 conan 实际走的 `patch_ng.fromfile(...).apply(strip=1)` 路径
  施加，产物 sha256 同样等于期望值（三条独立判据，不看 `--dry-run` 的 rc 单独说话）。
- 适用边界：任何在 OHOS 上把 `versionsort` 当 `scandir()`/`alphasort()` 同位比较器使用的包
  （GNU 扩展，musl 系 sysroot 不实现，且加 `_GNU_SOURCE` 无效）。

### 7. 消费者布局断言把 helper 落点写成 libexec（上游实际装进 lib/）

- 症状：versionsort 修好后 W3 首错挪到 `test()` ——
  `ConanException: missing mstpd artifacts: mstpd-utils dir`（test_package/conanfile.py:52，
  断言 `<pkg>/libexec` 存在），而 `find` 实物在 `<pkg>/lib/mstpctl-utils/`（5 枚 helper 文件俱在）。
- 根因：不是产物缺失，是**断言按 FHS 直觉写错了落点**；上游就是故意装到 lib/ 的——
  `Makefile.am:44` `utilsexecdir=$(libexecdir)/mstpctl-utils`；`configure.ac:11` 无条件把
  `exec_prefix` 置空（原文："there is no standard macro to override the default exec_prefix"），
  `configure.ac:34` 于是在 exec_prefix 为空时把 `libexecdir` 定为 `/lib` 而非默认 `/libexec`；
  本次构建生成的 `build-release/Makefile:376` 实拍 `libexecdir = /lib`。配方按 conan 范式
  `--prefix=/` + DESTDIR 落包 ⇒ helper 目录进 `<pkg>/lib/mstpctl-utils`。
- 最终方案（只把断言改准，同时把口径改严）：布局清单逐条取自**本次 conan create 产物自己的
  conanmanifest.txt**（16 件），断言由 6 项扩到 14 项（补 `mstp_restart` 别名、man5、
  bash completion、5 枚 helper 文件、utils 目录本身），今后少装任何一件都会红；
  两枚 `install-exec-hook` 建的 restart 符号链接指向**部署态绝对路径** `/bin/bridge-stp`
  （`--prefix=/` 下 sbindir=/bin），在暂存包目录内按定义不可解析 ⇒ 断言只判"packaged 条目存在"
  （`os.path.lexists`），解析行为改由 test_mstpd.sh 的 CAPTURE 段逐字记录，不混进断言、
  既不算通过也不算失败。
- 顺带收口：版本级 `manifest.yaml` 的 `artifacts` 段原来写 `libexec:`（该落点不存在），
  且漏了 `mstp_restart`、`mstpctl-utils-functions.sh`、`README.VLANs`、`LICENSE`；已按
  conanmanifest.txt 逐条重写为 16 项。
- 适用边界：上游自己改写 `libexecdir` 默认值、或经 `$(libexecdir)` 安装数据的 autotools 包，
  在 conan `--prefix=/` + DESTDIR 暂存范式下的落点判定。

## 运行面能力矩阵（只读探针逐项取证）

探针程序 = test_package/test_probe.c，每条打印**调用原样 + rc + errno + strerror**，成功行不报 errno（避免残值误读），
全部调用不带提权、不写包外路径。以下为本机实算结果（原文见 reports/capability-probes.txt，同机同二进制）。

| 能力 | 调用原样 | 实测 | 结论 |
|------|----------|------|------|
| netlink 路由套接字 | socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE) | rc=3 | 可用 |
| netlink bind | bind(nl, {AF_NETLINK, pid=0, groups=0}) | rc=0 | 可用 |
| netlink 链路转储 | send(RTM_GETLINK\|NLM_F_DUMP) + recv | rc=32 / rc=2660，links=2 bridge_kind=0 | 可用，但**无桥设备** |
| 原始套接字收 BPDU | socket(PF_PACKET, SOCK_RAW, htons(ETH_P_802_2)) | errno=13 Permission denied | **不可用** |
| 原始套接字（dgram 形态） | socket(PF_PACKET, SOCK_DGRAM, htons(ETH_P_802_2)) | errno=13 Permission denied | **不可用** |
| 控制通道 | socket(PF_UNIX,SOCK_DGRAM) + SO_PASSCRED + abstract bind(.mstp_server_probe) | 全部 rc=0 | 可用（与 E461 abstract 可用一致） |
| sysfs 类别目录 stat | stat("/sys/class/net") | rc=0 st_mode=040755 | 目录存在 |
| sysfs 列目录 | opendir("/sys/class/net") / scandir("/sys/class/net")（ctl_main.c:452 原调用） | errno=13 | **不可用** |
| sysfs 按名直读 | open("/sys/class/net/{lo,dummy0,tunl0}/ifindex") | errno=13 全部 | **不可用**（不止是列表被拒） |
| sysfs 正对照 | opendir("/sys/class/tty") | errno=13 | 与 net 同形态 ⇒ sysfs 域策略，非类别缺位 |
| 接口名索引 | if_indextoname(1..3) | lo / dummy0 / tunl0 | 内核有 3 个 netdev，netlink 侧可见 |
| 事件循环 | epoll_create(128) / EPOLL_CTL_ADD / epoll_wait / DEL | 全部 rc=0 | 可用（含 pipe 正对照） |
| 接口常规 ioctl | SIOCGIFFLAGS、SIOCGIFHWADDR（lo） | rc=0 | 可用（正对照） |
| 链路状态 ioctl | ioctl(SIOCETHTOOL, ETHTOOL_GLINK, lo) | errno=13 | **不可用** |
| 桥私有 ioctl | ioctl(SIOCGIFBR, lo) | errno=13 | **不可用** |
| pid 文件目录 | stat("/var/run")、stat("/run")、access("/var/run", W_OK) | errno=2 | 节点不存在（上游默认 pid 落点不可用） |
| termios（普查空白区补测） | posix_openpt / grantpt / unlockpt / tcgetattr / tcsetattr(cfmakeraw) | 全部 rc=0 | 可用；注：上游 mstpd 不使用 termios |

定性：mstpd 的**编译面与 CLI 面完整可用**；其守护职责所依赖的两条硬能力——PF_PACKET 原始套接字（BPDU 收发）与
/sys/class/net 桥属性读写——在本平台被拒（errno=13），且桥设备数为 0。因此本包按 E237（acpid 先例）方案一处置：
编译验证 + 全披露，不虚构运行结论；不改内核、不试 setcap/提权、不写"无法适配"结论。

## 依赖闭环（W0）

- 运行期依赖：无。configure.ac 只有 AC_CHECK_FUNCS(clock_gettime) 与 AC_SEARCH_LIBS(clock_gettime, rt)，
  零 PKG_CHECK_MODULES、零 AC_MSG_ERROR、零 AC_CHECK_LIB ⇒ 不存在链式未发布依赖，本包不需转等依赖。
- 编译期工具依赖：automake/1.18、libtool/2.5.4，preflight 实测两枚均已发布到 ohpcd。
- 版本号占用：preflight 实测 mstpd/0.2.0 未被占用（R37）。

## 测试口径说明（上游测试盘点）

- 一手清点：Makefile.am 无 check / TESTS / check_PROGRAMS 目标，树内无 tests 目录，configure.ac 无测试开关
  ⇒ **上游成体系自动化用例 0 条**，因此不存在"被跳过的 make check"。
- 上游另有一处内置自检 sanity_check()（main.c，由 main() 在选项解析后调用；-V 分支提前 return 不触发），
  内容为结构体尺寸等编译/运行期断言，成功打印 Sanity checks succeeded。它是守护启动路径的一部分，
  不是可独立执行的测试套件；本轮通过前台运行把它跑出来留证。
- 交付侧测试因此全部由本包 test_package 承担，见下文测试账本。

## 测试账本（本轮实算；权威取 reports/w3-local-ci.log 的 `*_RESULT=` 行）

- 上游成体系自动化用例 **0** 条（见上文"测试口径说明"）⇒ 不存在"被跳过的 make check"，
  分母不因本包适配而缩小。
- 交付侧消费者用例（`test_package/test_mstpd.sh` 的 ASSERT 段）：**可执行 8 / 通过 8 / 跳过 0 / 失败 0**
  （`MSTPD_TEST_SUMMARY executed=8 passed=8 failed=0`，w3-local-ci.log:1259）。
- 五维合计：上游 0；可执行 8；通过 8；跳过 0；失败 0。
- 门位读数（同一份日志）：`G0_RESULT=pass`、`KC_RESULT=pass`、`JC_RESULT=pass`、`L0_RESULT=pass`、
  `L1_RESULT=pass`、**`L2_RESULT=pass: bridge-stp version/help failed, mstpctl --version OK, mstpd failed`**、
  `L4_RESULT=pass: patches clean`、`L5_RESULT=pass: bin/ has content`。
  L2 里 `mstpd failed` 与 `bridge-stp` 失败都是**运行面能力墙**（PF_PACKET / `/sys/class/net` errno=13），
  不是构建面失败；构建面在本轮为 `error:=0`、`undefined symbol:=0`。
- 二进制真执行原样输出（同机同包）：
  - `mstpd -V` → `0.2.0-`，rc=0；`mstpctl -V` → `0.2.0-`，rc=0；`mstpctl --version` → rc=0；
    `mstpctl -h` → `Usage: mstpctl [options] [commands] …`，rc=0。
  - 前台 `mstpd -d -v 7` → `Version - 0.2.0-` → `int sanity_check(void): Sanity checks succeeded`
    → `error, int packet_sock_init(void): socket failed: Permission denied` →
    `Error … at main.c:184 verifying packet_sock_init() == 0`，rc=255（能力墙，见运行面矩阵）。
  - `mstpctl showtree br0` → rc=1，`int ctl_client_init(void): Couldn't connect to server`
    （守护未运行，符合预期）。
  - staged-install 绝对路径面（CAPTURE 原样）：`bin/mstp_restart` 与
    `lib/mstpctl-utils/mstpctl_restart_config` 的 target 均为 `//bin/bridge-stp`、
    `resolves_inside_package=no`；`bin/bridge-stp:72` 为
    `config_cmd='/lib/mstpctl-utils/mstp_config_bridge'`（上游 @template@ 替换结果）。

## 安全边界（已遵守）

- 未改内核、未加载模块、未试 setcap/提权、未 kill 任何进程、未动他人 worktree 与共享缓存。
- 探针只读：不写包外路径（pid 目录只做 stat/access 判定，不创建），不请求任何特权。
- 所有临时产物落在 ~/tmp/uc2/mstpd/ 与本任务 CONAN_HOME，未在家根落散文件。

### 对话 #1：取源为什么用 GitHub tag 归档

- 问：Debian 池里有 .orig，官方 release 页有没有资产？
- 答：上游 release 0.2.0 未上传任何发布资产，官方唯一机器可读源是 tag 归档，且 tag 名不带 v 前缀
  （v0.2.0 形态 404）。实物 117075 字节，本机自算 sha256 见 conandata.yml。
  Debian 池 .orig 的指纹与它不相等属正常（.orig 是 Debian 重打包形态），按 PF7/R39 配方只写官方址 + 自算哈希，
  不引用池址。

### 对话 #2：为什么不声明 autoconf/m4

- 问：既然要 autoreconf 自举，为什么不把 autoconf 全家桶都 tool_requires？
- 答：CI 干净环境里 SDK 的 /data/service/hnp/bin 已经有 autoconf 2.72 / autom4te / m4 / perl，
  缺的只是 aclocal/automake/libtoolize；而声明 autoconf/2.72 会连带拉进 OHOS 版 perl，其 XS 模块与 SDK perl
  解释器冲突（Perl_my_cxt_init 找不到符号）——这条写在已合入的 accel-config/4.1.9 配方注释里，本包照抄该取舍。
  本机实测也支持：autoconf --version 直接可用，automake --version 因 shebang 指向不存在的解释器而失败。

### 对话 #3：跑不起来要不要就此收尾

- 问：PF_PACKET 与 sysfs 桥属性都被拒，是否按"无法适配"处理？
- 答：不。构建面与 CLI 面完整可用、消费者用例真跑通，内核面缺口属平台能力事实，按 E237（acpid 先例）方案一
  处置：编译验证 + 全披露，逐项 errno 与调用原样入表，不虚构运行结论，也不自行下"无法适配"定性。

## 交付物

| 文件 | 说明 |
|------|------|
| archives/m/mstpd/0.2.0/conanfile.py | 配方（自举 + E091 守卫 + 三元组钉死 + 前缀受控） |
| archives/m/mstpd/0.2.0/conandata.yml | 官方取源址与自算 sha256 + 两枚补丁登记 |
| archives/m/mstpd/0.2.0/patches/0001-netif-utils-ethtool-speed-ohos.patch | 内核 static inline `ethtool_cmd_speed()` 就地展开（适配点 5） |
| archives/m/mstpd/0.2.0/patches/0002-ctl-main-versionsort-alphasort-ohos.patch | `scandir` 比较器 `versionsort`→`alphasort` 的 `__OHOS__` 守卫回退（适配点 6） |
| archives/m/mstpd/0.2.0/test_package/conanfile.py | 布局校验 + 探针编译 + 执行消费者脚本 |
| archives/m/mstpd/0.2.0/test_package/test_mstpd.sh | 消费者断言与运行面取证脚本（输出全走绝对路径） |
| archives/m/mstpd/0.2.0/test_package/test_probe.c | 能力面探针（上游真实调用面，逐条带调用原样） |
| archives/m/mstpd/0.2.0/test_package/MANIFEST.yml | 上游测试盘点与本轮用例清单 |
| archives/m/mstpd/README.md、manifest.yaml、commands.json | 软件级三件套（R38/PF8 要求 CLI 包声明 commands.json） |
| archives/m/mstpd/0.2.0/manifest.yaml | 版本级编译元数据 |

## 声明（3+2）

- **适配路径**：B（本包新增 1 条机制条目草稿：OHOS sysroot 无 GNU `versionsort(3)` 时
  `scandir()` 比较器回退 POSIX `alphasort(3)`；判档依据与"为什么不是 hit"见该草稿的边界节）
- **使用知识库**：E091（knowledge/doc/E091.md，errno 面命中，处置改用 sysroot 自带守卫以避 PF5）、
  E521（knowledge/doc/E521.md，libtoolize 内嵌 SED 路径）、E116 与 E049（knowledge/doc/E116.md、
  knowledge/doc/E049.md，镜像内 automake 的 perl shebang 断裂，据此改走 tool_requires）、
  E237（knowledge/doc/E237.md，守护进程运行面缺失时的编译验证 + 全披露口径）、
  E461（knowledge/doc/E461.md，AF_UNIX abstract 套接字可用性的判读基线）、
  E386 与 E490（HMDFS getcwd 家族：configure 的 `working directory cannot be determined`
  与 config.status 临时目录拒写两段失败，处置见 conanfile.py `build()` 内注释）
- **知识库扩展**：`knowledge/drafts/DRAFT-mstpd-0.2.0-ohos-dirent-missing-versionsort-alphasort-fallback.kv`
  ＋同名 `.md`（本包适配点 6 的机制；E091 的处置层次差仍按上条说明，不进本条范围）
- **关联 Issue**：待主理窗在本 PR 上创建后回填号（执行棒不建 Issue、不动 PR 标题）
---

**编译结束**: 2026-09-27 00:39
**最终状态**: built
