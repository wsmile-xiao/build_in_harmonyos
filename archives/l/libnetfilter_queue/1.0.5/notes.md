# libnetfilter_queue 1.0.5 — 编译笔记

> 档案创建时间: 2026-09-09
> 最后更新: 2026-09-09
> 状态: ✅ built（v3 Conan 配方新建档案）

---

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | libnetfilter_queue |
| 版本 | 1.0.5 |
| 描述 | NFQUEUE 用户态库：接收内核排队报文并下发裁决 |
| 构建系统 | autotools（tarball 带 pregenerated configure，Autoconf 2.69） |
| 语言 | C |
| 许可证 | GPL-2.0-or-later |
| 依赖 | libmnl >= 1.0.3、libnfnetlink >= 0.0.41（PKG_CHECK_MODULES 硬要求，无关闭开关） |
| soname | libnetfilter_queue.so.1（LIBVERSION 6:0:5；本档案 static-only 交付） |

---

## 二、v3 Conan 配方（2026-09-09）

本档案为 v3 全新建档（此前 archives/l/libnetfilter_queue/ 目录不存在），
对照同族两个已发布先例逐项对齐格式：

- `archives/l/libnfnetlink/1.0.2` — conanfile/manifest/notes 基准
- `archives/l/libmnl/1.0.5` — 最新交付形态基准（static-only、test bash 包裹、
  HMDFS configure 补丁模板）

### 文件清单

| 文件 | 说明 |
|------|------|
| conanfile.py | Autotools 配方：export_conandata_patches + basic_layout + PkgConfigDeps；requires libmnl/1.0.5 + libnfnetlink/1.0.2；generate() 显式 `--enable-static --disable-shared` 并把 PKG_CONFIG_PATH 指向 generators 目录；build() 末尾 `autotools.make(target="check")`；cpp_info.libs=["netfilter_queue"] |
| conandata.yml | sources(url + sha256) + patches（Conan 2.x list 格式，L0f 强制） |
| patches/0001 | sockaddr_storage 守卫（9 个 TU，见决策 3） |
| patches/0002 | build-aux/config.guess HarmonyOS 识别（同 libmnl 0001 模板） |
| patches/0003 | build-aux/config.sub ohos-linux / linux-ohos 三元组（同 libmnl 0002 模板） |
| patches/0004 | configure HMDFS mktemp=TMPDIR+chmod 755（同 libmnl 0003 模板，本库 configure 同为 Autoconf 2.69 同构代码块） |
| test_package/ | 消费者测试（conanfile.py / CMakeLists.txt / test.c / MANIFEST.yml） |
| manifest.yaml | 版本级 manifest（新建，字段参照 libnfnetlink 先例） |

### 关键决策

1. **交付形态 static-only**（`--enable-static --disable-shared`）。
   沿用 libmnl/1.0.5 已验证机理：HarmonyOS（CMAKE_SYSTEM_NAME=HarmonyOS）下
   CMake 对 imported shared 库不注入任何 RPATH/RUNPATH，叠加消费环境不注入
   依赖 libdir 的 LD_LIBRARY_PATH，shared 交付的 out-of-tree 消费者运行期
   无任何搜索路径（`Error loading shared library lib*.so.*`）；static 交付
   在链接期吸收依赖。该机理经 libmnl run 设备实测，暂未沉淀为知识条目。
   注意上游 configure.ac 有 `AC_DISABLE_STATIC`，必须显式 `--enable-static`
   覆盖，否则只传 `--disable-shared` 会 shared/static 双空（libmnl 先例实测）。
   libnetfilter_queue 非 OHOS 系统同名库，R26 不是决策驱动。

2. **依赖与 pkg-config**：configure PKG_CHECK_MODULES 硬要求
   libnfnetlink>=0.0.41 + libmnl>=1.0.3。requires 取仓内已发布版本
   （libmnl/1.0.5、libnfnetlink/1.0.2；仓库可用性优先于 CCI 的 libmnl/1.0.4
   pin）。**conan 2.29.1 不会自动导出 PKG_CONFIG_PATH**（本机探针实测：
   conan install + PkgConfigDeps 后，generators 目录正确产出 libmnl.pc /
   libnfnetlink.pc 代理文件，但 conanbuild*.sh 全部没有 PKG_CONFIG_PATH），
   因此 generate() 显式 `env.prepend_path("PKG_CONFIG_PATH",
   self.generators_folder)`。同族先例均无外部依赖，此为 netfilter 家族首个
   带依赖配方。

3. **sockaddr_storage 守卫覆盖 9 个 TU（超出 Scout 预设的单文件）**。
   Scout 预设仅在 src/libnetfilter_queue.c L30-33 插入守卫；实配时按设备
   sysroot 头包含链逐一核对（OHOS NDK sysroot，bionic 风格 uapi 拷贝），
   冲突条件 = 「musl sys/socket.h（直接 include，或经 netinet/in.h、
   netinet/tcp.h、net/if_arp.h、libmnl.h、libnfnetlink.h 间接）」与
   「sysroot linux/socket.h（经 linux/netlink.h 间接）」在同一 TU 交汇
   （sysroot linux/socket.h 无条件重定义 struct sockaddr_storage，无
   __UAPI_DEF_* 协调）。本库捆绑 UAPI 头仅 include/linux/netfilter/
   nfnetlink_queue.h，`-I$(top_srcdir)/include` 无法像 libmnl 那样以捆绑
   副本遮蔽 sysroot 的 linux/netlink.h，故守卫必须逐 TU 落位：
   - src/libnetfilter_queue.c（netinet/in.h + sys/socket.h + libnfnetlink.h）
   - src/nlmsg.c（libmnl.h L15 同时拉 sys/socket.h 与 linux/netlink.h）
   - src/extra/{checksum,ipv4,ipv6,tcp,udp}.c（netinet/*.h + 公共头链）
   - src/extra/pktbuff.c —— 不含任何 linux 头，**无需**守卫
   - utils/nfqnl_test.c、examples/nf-queue.c —— make check 的
     check_PROGRAMS 同样交汇（否则 make check 失败）
   test_package/test.c 用同型守卫（E091/E119 消费侧变体）。
   守卫块文本与 libnfnetlink 0002-0004 补丁逐字一致。
   知识申报说明：守卫模式已被知识图谱 E091/E119 覆盖，本轮不新增草稿。

4. **libnfnetlink 自带 linux_nfnetlink.h 与 sysroot nfnetlink.h 双定义
   （CI round-01 实测发现并回修）**。CI round-01 在 nlmsg.lo 失败：
   `enum nfnetlink_groups`/`struct nfgenmsg` 重定义——已安装 libnfnetlink
   包自带 libnfnetlink/linux_nfnetlink.h（守卫 `_NFNETLINK_H`，2008 版内核
   头拷贝），与 sysroot linux/netfilter/nfnetlink.h（守卫
   `_UAPI_NFNETLINK_H`）守卫名不同、内容相同，同 TU 双 include 即冲突。
   冲突 TU 仅 2 个：src/nlmsg.c（捆绑 nfnetlink_queue.h 先拉 sysroot
   nfnetlink.h）与 examples/nf-queue.c（显式 include sysroot nfnetlink.h）。
   最小修复：在这两处守卫块中追加预定义 `_NFNETLINK_H`，抑制包内副本、
   沿用先一步包含的 sysroot 副本（内容等价且为超集）；其余 TU 中包内副本
   仍是唯一来源，不受影响。libnfnetlink 包自身的 recipe 不在本 run 边界内，
   不改动；若未来有更多消费者踩同一问题，建议 Curator 在 libnfnetlink
   侧评估根治（如 cpp_info system_package 语义或补丁统一守卫）。

5. **上游无 testsuite（NO_UPSTREAM_TESTS 口径，同 libnfnetlink/libmnl）**：
   `make check` 仅构建 check_PROGRAMS（utils/nfqnl_test、examples/nf-queue，
   均链接 ../src/libnetfilter_queue.la），上游验证 = 编译+链接；运行需内核
   NFQUEUE + CAP_NET_ADMIN，不属 make check 执行范围。真实运行验证由
   test_package 消费者冒烟承担：nfq_nlmsg_put 构造 NFQNL_MSG_VERDICT /
   NFQNL_MSG_PACKET 消息 + nfq_nlmsg_verdict_put/_put_mark 属性回环，
   纯用户态无需 CAP_NET_ADMIN（assertion_count=4）。

### 观察项（未改动）

- 上游 `src/Makefile.am` 的 `libnetfilter_queue_la_LDFLAGS` 含
  `-Wc,-nostartfiles -lnfnetlink`（后者与 LIBADD 冗余）。static-only 交付下
  libtool 以 ar 归档，不经过该链接开关；本轮按最小补丁原则未动。若未来
  改回 shared 交付需重新评估（-nostartfiles 会去掉 CRT 启动文件）。

---

## 三、源码修改清单

| 文件 | 原因 | 补丁状态 |
|------|------|---------|
| src/libnetfilter_queue.c | sockaddr_storage 冲突 | 0001（守卫插入 include 链 L31/L33 之间） |
| src/nlmsg.c | 同上（libmnl.h 双拉） | 0001 |
| src/extra/checksum.c | 同上 | 0001 |
| src/extra/ipv4.c | 同上 | 0001 |
| src/extra/ipv6.c | 同上 | 0001 |
| src/extra/udp.c | 同上 | 0001 |
| src/extra/tcp.c | 同上 | 0001 |
| src/extra/pktbuff.c | 无冲突（不含 linux 头） | 未改动 |
| utils/nfqnl_test.c | sockaddr_storage 冲突（make check 目标） | 0001 |
| examples/nf-queue.c | 同上 | 0001 |
| build-aux/config.guess | HarmonyOS 识别 | 0002 |
| build-aux/config.sub | ohos 三元组 | 0003 |
| configure | HMDFS mktemp 权限 | 0004 |

---

## 四、知识提取

### HMDFS mktemp 权限问题（沿用既有结论）
- 与 libmnl/libnfnetlink 同型：`(umask 077 && mktemp -d "./confXXXXXX")`
  在 HMDFS 上产生 owner 不可写目录；补丁 0004 按 libmnl 0003 模板改
  `${TMPDIR:-/tmp}` + chmod 755。

### conan 2.29.1 PkgConfigDeps 不导出 PKG_CONFIG_PATH（本轮实测）
- PkgConfigDeps 在 generators 目录产出依赖代理 .pc，但 conanbuild*.sh 不含
  PKG_CONFIG_PATH；PKG_CHECK_MODULES 型 autotools 消费者必须在 generate()
  显式注入。是否沉淀新知识条目交由 Curator 评估（本轮未擅自创建草稿）。

---

**编译结束**: 2026-09-09
**最终状态**: built
