# kamailio-lost 6.0.6 适配笔记

## 编译环境
- 构建系统: makefile（kamailio 经典 Makefile 体系，非 autotools/cmake）
- 编译日期: 2026-09-28
- 编译器: clang（OHOS SDK 26.0.0.18，aarch64-unknown-linux-ohos）
- 状态: published

## 一、适配对象与打包口径

kamailio 的 `lost` 模块（`src/modules/lost/lost.so`）：实现 **HELD**（RFC 5985）与
**LOST**（RFC 5222）位置查询，脚本侧入口 `lost_query()` / `lost_held_query()` /
`lost_held_dereference()`，返回体是 PIDF-LO XML。

打包口径与同源码树先例一致（`archives/k/kamailio-slack/6.0.6`、
`archives/k/kamailio-tls/6.0.6`、`kamailio-snmpstats/6.0.6`）：
取官方源码包全量构建，**只编译打包目标模块**，不提供 kamailio 本体包——模块 `.so` 由
kamailio 运行时 `loadmodule "lost.so"` 加载到模块目录使用。

**lost 与先例的结构性差异**：它是本源码树里第一个**同时依赖两个第三方原生库**的模块
（XML 解析用 libxml2、HTTP 出站走 curl 链接项），而先例（slack/tls/snmpstats/debugger）
都只有一个第三方依赖。这个差异直接决定了第三方库探测的落地方式，见第五节。

## 二、编译步骤

```bash
# 1) 取官方源码包（sha256 见 conandata.yml）
#    https://www.kamailio.org/pub/kamailio/6.0.6/src/kamailio-6.0.6.tar.gz
# 2) 生成构建配置（必须，否则报 No rule to make target 'cfg-defs'）
make cfg include_modules=lost \
     OS=linux LOCALBASE=<不存在的路径> XML2CFG= CURL_BUILDER=
# 3) 构建目标模块
make modules modules=modules/lost -j1 \
     OS=linux LOCALBASE=<不存在的路径> XML2CFG= CURL_BUILDER=
# → src/modules/lost/lost.so
```

其中头/库搜索路径不通过 LOCALBASE 传，而是用环境变量**逐依赖**给出：

```bash
CPATH=<libxml2 包目录>/include/libxml2:<libxml2 包目录>/include:<curl 包目录>/include
LIBRARY_PATH=<libxml2 包目录>/lib:<curl 包目录>/lib
```

`<libxml2 包目录>` / `<curl 包目录>` 即制品仓 `libxml2/2.15.3.1` 与 `curl/8.15.0.1`
的 `package_folder`（各含 `include/`、`lib/`）。两条命令都已在 `conanfile.py` 的
`build()` 中实现，`OS=linux` 与置空的探测变量以 make 命令行变量传入。

## 三、依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| libxml2 | 2.15.3.1 | 模块 Makefile 的 `LIBS += -lxml2`；PIDF/HELD XML 解析（`xmlReadMemory` / `xmlXPath*` 等 31 个符号）；制品仓已发布二进制 |
| curl | 8.15.0.1 | 模块 Makefile 的 `LIBS += -lcurl`；制品仓已发布二进制（与 kamailio-slack/6.0.6 同一版本） |

运行时模块依赖（非 conan 依赖，属 kamailio 侧模块加载顺序）：`http_client` 模块。
`lost.c` 的 `mod_init()` 调 `httpc_load_api(&httpapi)` → `find_export("bind_http_client")`，
故 kamailio 侧配置里**必须先 `loadmodule "http_client.so"` 再 `loadmodule "lost.so"`**；
本包只提供 `lost.so`。

## 四、上游测试（R51 三步法）

### 1) 清点（口径可复现）

```bash
tar tzf kamailio-6.0.6_src.tar.gz | grep -E '/(test|tests)/' | grep -v '/$' | wc -l   # → 17
```

| 分组 | 文件数 | 性质 |
|------|--------|------|
| `utils/kamctl/dbtextdb/tests/` | 10 | `dbtextdb_test.py` 的用例数据 |
| `src/modules/janssonrpcc/test/` | 3 | jsonrpc-c 模块脚本 + 配置 |
| `src/modules/rtpproxy/test/` | 3 | rtpproxy 模块配置 + 命令行记录 |
| `src/modules/tm/test/` | 1 | tm 模块开发期 IPC 清理脚本 |
| **合计** | **17** | |

`lost` 模块自身源码目录 `src/modules/lost/` 内**无测试文件**、无 `check`/`ctest` 目标注册
（该目录 17 个文件：`CMakeLists.txt` `Makefile` `README`
`doc/{Makefile,lost.xml,lost_admin.xml}` `functions.{c,h}` `lost.c` `naptr.{c,h}`
`pidf.{c,h}` `response.{c,h}` `utilities.{c,h}`）。

### 2) 实跑

17 个文件中唯一自包含、无需运行中 kamailio 实例与外部网络的上游测试：

```bash
cd utils/kamctl/dbtextdb && python3 dbtextdb_test.py -v
# testExecute / testOpenTable / testParseQuery ... ok
# Ran 3 tests in 0.035s — OK（fixtures: tests/ 下 10 个数据文件）
```

该命令已内置在 `conanfile.py` 的 `build()` 末尾（`_run_upstream_tests()`），非零退出即构建失败，
因此「上游测试真实执行」与「产物完整性」在同一次 `conan create` 内完成，无跳过空间。

### 3) 回填

- 上游测试用例通过率：**3/3（100%）**
- 声明 N 与实测 N 一致：**N = 17**（清点口径 = 官方源码包内 `test/`、`tests/` 目录文件数）
- 未独立执行的 14 个文件逐项技术原因见 `test_package/MANIFEST.yml` 的
  `upstream_tests[].not_executed_reason`（数据文件 / 需 kamailio 主程序 / 需外部进程 / 破坏性脚本）

## 五、遇到的问题与解决方案

### 问题 1（主因）：单值 LOCALBASE 无法同时承载两个依赖

**根因**：`src/modules/lost/Makefile` 为 libxml2 与 curl 各写了一段
「宿主探测 / LOCALBASE 兜底」二选一分支，但**兜底侧共用同一个 `$(LOCALBASE)`**：

```make
ifneq ($(XML2CFG),)
	DEFS += $(shell $(XML2CFG) --cflags )
	LIBS += $(shell $(XML2CFG) --libs)
else
	DEFS+=-I$(LOCALBASE)/include/libxml2 -I$(LOCALBASE)/include
	LIBS+=-L$(LOCALBASE)/lib -lxml2          # ← 同一个 LOCALBASE
endif
ifneq ($(CURL_BUILDER),)
	DEFS += $(shell $(CURL_BUILDER) --cflags )
	LIBS += $(shell $(CURL_BUILDER) --libs)
else
	DEFS+=-I$(LOCALBASE)/include
	LIBS+=-L$(LOCALBASE)/lib -lcurl          # ← 同一个 LOCALBASE
endif
```

`LOCALBASE` 在 `Makefile.defs:479-533` 里是按 OS 赋值的**单值标量**（linux 分支为
`/usr/local`，默认值也是 `/usr/local`）；而 Conan 2 给每个依赖一个独立包目录，
libxml2 与 curl 不共享前缀。于是"两个 `-lX` 共用一个 `-L/-I` 前缀"在 Conan 2 下
**结构上不可满足**。

**受控实验（同一棵源码树、同一套环境，只改变量）**：

| 构建 | 第三方库变量 | 结果 |
|------|--------------|------|
| A：先例手法的直接推广 | `LOCALBASE=<curl 包目录> XML2CFG= CURL_BUILDER=`（= kamailio-slack/6.0.6 的做法） | **失败**：`pidf.c:58:10: fatal error: 'libxml/parser.h' file not found`（`-I` 落到了 curl 包目录）；连带 `naptr.c` / `functions.c` 同样失败 |
| B：逐依赖注入 | `LOCALBASE=<不存在的路径> XML2CFG= CURL_BUILDER=` + `CPATH`/`LIBRARY_PATH` 按依赖逐个列出 | **通过**：`lost.so` 715136 字节，`readelf -d` 的 `DT_NEEDED` = `libxml2.so.16` / `libcurl.so` / `libc.so` |

先例的手法之所以"恰好够用"，仅仅因为 slack/tls/snmpstats/debugger 都只有**一个**
第三方依赖——单值前缀刚好等于依赖数。lost 把这个隐含前提打破了。

**被否决的两条替代路线（均实测）**：

1. **用 pkg-config 修补**（`XML2CFG="pkg-config --define-variable=prefix=<libxml2包> libxml-2.0"`、
   `CURL_BUILDER="pkg-config --define-variable=prefix=<curl包> libcurl"`）：
   - 两个包的 `.pc` 里的 prefix 都是错的——`libxml-2.0.pc` 为 `prefix=/usr/local`，
     `libcurl.pc` 为 `prefix=<构建期 conan cache 目录>`；不修就得不出正确路径，故必须 `--define-variable=prefix=`；
   - 修好后 `libxml-2.0 --cflags/--libs` 正常，但 `libcurl --cflags` **直接 rc=1**：
     `Package openssl was not found in the pkg-config search path`（`libcurl.pc` 带
     `Requires.private: openssl,zlib`，pkg-config 算 `--cflags` 时会遍历它）。
     ⇒ 该路线需要额外把 openssl/zlib 的 `.pc` 也塞进 `PKG_CONFIG_PATH`，而这些 `.pc`
     的 prefix 同样不可信，会引入新的不可控 `-I`。
2. **造一个"联合前缀"目录**（把两个包目录的 `include/`、`lib/` 用符号链接聚到一处，
   再把这个目录当 `LOCALBASE`）：能同时满足两段兜底分支，但要在构建期维护符号链接农场，
   且链接关系随依赖绝对路径变化而失效；相比之下逐依赖注入没有中间层。

### 问题 2（同源）：HarmonyOS 不匹配 kamailio 的任何 OS 分支

**根因**：`src/Makefile.defs:125`

```make
OS := $(shell uname -s | sed -e s/SunOS/solaris/ -e s/CYGWIN.*/cygwin/ \
		 | tr "[A-Z]" "[a-z]" | tr "/" "_")
```

设备 `uname -s` = `HarmonyOS` → `OS=harmonyos`，而后续所有平台分支只认
`solaris / netbsd / linux / gnu_kfreebsd / freebsd / openbsd / dragonfly / darwin / cygwin`
——于是**整套平台能力宏被静默跳过**。

**实测差异**（同一棵树，只改 `make cfg` 的 OS 值，比对生成的 `src/config.mak` 的 `C_DEFS`）：

```bash
make cfg include_modules=lost            # → OS= harmonyos
make cfg OS=linux include_modules=lost   # → OS= linux
comm -23 <(tr ' ' '\n' < C_DEFS_linux) <(tr ' ' '\n' < C_DEFS_harmonyos)
```

linux 分支比 harmonyos 分支多 **11 个宏**（`LIBS` 实测无差异）：

| # | 宏 | 缺了会怎样 |
|---|----|-----------|
| 1 | `-DHAVE_GETHOSTBYNAME2` | **硬失败**：`core/resolve.h:290` 直接 `#error neither gethostbyname2 or getipnodebyname present`（编译中断） |
| 2 | `-DHAVE_UNION_SEMUN` | 静默：SysV 信号量结构体取值形态不同 |
| 3 | `-DHAVE_SCHED_YIELD` | 静默：退化为忙等 |
| 4 | `-DHAVE_MSG_NOSIGNAL` | 静默：写 socket 改用信号屏蔽路径 |
| 5 | `-DHAVE_MSGHDR_MSG_CONTROL` | 静默：辅助数据收发路径不同 |
| 6 | `-DHAVE_ALLOCA_H` | 静默 |
| 7 | `-DHAVE_TIMEGM` | 静默 |
| 8 | `-DHAVE_SCHED_SETSCHEDULER` | 静默 |
| 9 | `-DHAVE_IP_MREQN` | 静默：组播结构体名不同 |
| 10 | `-DHAVE_SELECT` | 静默：I/O 等待实现选择 |
| 11 | `-DUSE_RAW_SOCKS` | 静默 |

此外 `OS` 值本身还决定 `-DOS='harmonyos_'` / `-D__OS_harmonyos` 与
`-DOS='linux_'` / `-D__OS_linux`——核心代码里 `__OS_linux` 控制 socket 选项分支
（`socket_info.c` / `udp_server.c` / `tcp_options.h` / `daemonize.c`）与 `SO_REUSEADDR`
一类的 Linux 语义。

**为什么"逐个补宏"是症状级、而固定 `OS=linux` 是根因级**：补宏至少要补 11 个，其中 1 个是
编译中断（可见），另外 10 个是**静默行为差异**（不可见，只能靠逐项审计 `C_DEFS` 差异发现）；
而 OHOS 的工具链三元组本身就是 `aarch64-unknown-linux-ohos`、内核是 Linux、libc 是 musl，
这些宏与 `__OS_linux` 分支描述的正是这台设备真实具备的能力，所以 `OS=linux` 是"按上游
自己的平台分类法给出正确取值"，不是绕过检查。副作用可控：CI 主机本身是 Linux，
`uname -s` 已经是 `Linux`，因此这一行在 CI 上是恒等变换，只改变 HarmonyOS 原生构建的行为。

**踩坑记录（值得单独记）**：`make cfg` 生成的 `src/config.mak` 会把
`OS` / `C_DEFS` / `LOCALBASE` / `CFLAGS` …整个烘死。如果先用默认 OS 跑
`make cfg`、再只在 `make modules` 命令行补 `OS=linux`，**无效**：

| 构建 | 命令 | 结果 |
|------|------|------|
| B1 | `make cfg`（默认）→ `make modules`（不传 OS） | 失败：`core/resolve.h:290:2: error: neither gethostbyname2 or getipnodebyname present` |
| B2 | `make cfg`（默认）→ `make modules OS=linux` | **仍失败**：同上。`config.mak` 的 `C_DEFS=…` 普通赋值覆盖了按 `OS=linux` 重新算出的宏集 |
| C | `make cfg OS=linux` → `make modules OS=linux` | **通过**：`lost.so` 构建成功 |

⇒ 结论：`OS` 必须在 `make cfg` 阶段就给对，且两步保持同一个值。本配方两条命令都传。

### 问题 3：探测变量必须显式置空

`ifeq ($(CROSS_COMPILE),)` 为真时会优先用宿主 `xml2-config` / `pkg-config`——
CI 容器里若装了 `libxml2-dev`/`libcurl-dev`，会把构建机（x86_64）的头库路径直接
带进 aarch64 交叉编译。故两个探测变量都在 make 命令行显式置空
（同时 `CROSS_COMPILE` 为空意味着走"非交叉"分支，但产物仍由 profile 指定的
`/data/service/hnp/bin/clang` 生成 aarch64 目标——这与同族先例的处理一致）。

### 问题 4：`lost.so` 链接了 libcurl，却不使用任何 curl 符号

`readelf --dyn-syms` 的未定义集里**没有任何 `curl_*`**；模块所有出站 HTTP 都经
`httpapi.http_connect` / `httpapi.http_client_query_c`（http_client 模块 API）。
`DT_NEEDED` 里的 `libcurl.so` 是模块 Makefile `-lcurl` 的链接期产物。
两个后果：① 运行时真正需要先 `loadmodule "http_client.so"`；
② 加载 `lost.so` 时仍需能解析到 `libcurl.so`（`DT_NEEDED` 未满足会直接 dlopen 失败），
故消费者侧必须把 curl 包的 `lib/` 放进加载器搜索路径——已写进 `test_package`。

## 六、验证结果

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

本机（HarmonyOS PC 真机，aarch64）实测输出：

| 层 | 内容 | 结果 |
|----|------|------|
| 层 1 | 产物结构（ELF 头 / DT_NEEDED / 入口符号 / 许可证） | **15 passed, 0 failed** |
| 层 2 | 消费者 E2E（dlopen + 最小核心桩 + HELD 全链路） | **45 passed, 0 failed** |
| — | 合计 | **60 passed, 0 failed** → `ALL CHECKS PASSED` |

层 2 的 `lost_held_dereference()` 真实覆盖五条分支：

| 用例 | 输入 | 期望 | 实测 |
|------|------|------|------|
| LocByVal | presence + `location-info` | 200+2 = 202 | 202 |
| LocByRef | presence + `locationURI` | 200+1 = 201 | 201 |
| 非法根元素 | `<notHeld/>` | 400 | 400 |
| HTTP 非 2xx | 桩返回 404 | 400（解析前拒绝） | 400 |
| 空响应体 | `len == 0` | 400 | 400 |

并断言了投递面：`Content-Type: application/held+xml;charset=utf-8`、`Accept` 含
`application/pidf+xml`、POST 正文为 libxml2 生成的 `locationRequest`
（含 held 命名空间、`responseTime="5"`、归一化后的 `geodetic locationURI`），
以及 pidf/err 两个可写伪变量的回写值。

产物结构实测：

```
lib/kamailio/modules/lost.so   715136 bytes
  DT_NEEDED: libxml2.so.16, libcurl.so, libc.so
  DT_RPATH/DT_RUNPATH: 无
  sha256: b2869b304994d5514839406cf4f013be1f8a5249f7b47492f3d7fb7fea479270  (run#2, build folder kamai87b8dfb686e9a)
  sha256: 3360fe9efc8e7d672fa3f57e3104e7305d229848c4c220694ca5b192a220b985  (run#1, build folder kamaibcf751b56f698)
licenses/COPYING
```

> ⚠️ **产物 sha256 不可复现，且与本配方的构建变量无关**：`lost.so` 内含编译期源码
> 绝对路径字符串，实测 `strings -a` 可见
> `/storage/Users/.../.conan2/p/b/kamai<build-id>/b/src/src/modules/lost` —— 该路径含
> Conan 的 build folder 编号，因此**换一个 build folder 重新构建，产物哈希就会变**。
> 两次构建的差异实测为 `cmp -l` 共 **86 行**、集中在单一连续区间，即该路径字符串本身；
> 其余内容完全一致（两者均 715136 字节，`DT_NEEDED` 相同）。
> 对照：本配方使用的 `LOCALBASE=<不存在的路径>` 并未泄漏进产物
> （`strings -a lost.so | grep -c no-single-localbase-retired` 实测 **0**）。
> ⇒ 对外引用产物指纹时，以「同一 build folder 内自洽」为准，不要跨构建目录比对 sha256。

## 七、交付物

| 文件 | 说明 |
|------|------|
| `lib/kamailio/modules/lost.so` | 目标模块（AArch64 ELF 共享对象） |
| `licenses/COPYING` | 上游许可证正文（GPL-2.0-or-later） |

## 八、注意事项

- 模块加载顺序：`http_client.so` 必须在 `lost.so` 之前加载（`mod_init()` 绑定其 API）。
- 本包不含 kamailio 本体：`lost.so` 需放入既有 kamailio 安装的模块目录后由运行时加载；
  加载器还需能找到 `libxml2.so.16` 与 `libcurl.so`（`DT_NEEDED`）。
- `lost` 无 KEMI 导出（`dynsym` 无 `mod_register`，与同族 `kamailio-slack` 不同），
  只能从 kamailio 脚本路由调用。
- `locations` 参数（`lost_query()` 的第 1 个参数）解析出的连接信息需要 `http_client`
  的 `curl_connect`/`curlcon` 配置支持；本包只负责 `lost.so` 本身的构建与打包。