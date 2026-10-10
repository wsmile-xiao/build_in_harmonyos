# memcacheq 0.2.1 — HarmonyOS PC 适配笔记

- **软件**: MemcacheQ（Steve Chu）— 基于 memcache 协议的持久化 FIFO 消息队列守护进程
- **版本**: 0.2.1（2008 年上游最后一版）
- **许可**: BSD-3-Clause
- **上游源**: https://distfiles.macports.org/memcacheq/memcacheq-0.2.1.tar.gz
  （SHA256 `ace33313568959b5a301dda491f63af09793987b73fd15abd3fb613829eda07e`）
- **构建系统**: autotools（tarball 自带 configure，无 config.guess/config.sub，无 AC_CANONICAL_HOST）
- **包类型**: application（单可执行 `bin/memcacheq`，无库）
- **依赖**: `libevent/2.1.12@ohpcd/stable`、`db/6.2.32@ohpcd/stable`（均为共享库）

## 1. 软件与接口

memcacheq 把 BerkeleyDB 当持久层、libevent 当事件循环，对外暴露 memcache
文本协议（TCP，默认端口 22201）：`set <queue> 0 0 <bytes>` 入队（回
`STORED`），`get <queue>` 出队（回 `VALUE <queue> 0 <bytes>` + 数据 +
`END`，队列空时仅 `END`），另有 `delete`（不存在回 `NOT_FOUND`）、
`stats` / `stats queue` / `stats reset`、`version`、`quit`，未知命令回
`ERROR`。核心语义：**每个 key 是一条独立 FIFO 队列**，get 即消费（出队
即删），messages 落盘于 `-H` 指定的 BDB 环境。

CLI：`-p port`、`-U udp-port`、`-l addr`、`-H dbhome`、`-N`（内存缓冲）、
`-R`（每队列最大读写请求数）、`-T`（读超时）、`-v/-vv` 日志、`-h` usage、
`-i` license。守护进程需可写的 dbhome 目录。

## 2. 构建方式研究结论

- `configure` 用**自己的**探测循环找依赖：`--with-libevent=PATH` 找
  `event.h` + `libevent` 里的 `event_loop`；`--with-bdb=PATH` 找 `db.h`
  + `libdb` 里的 `db_create`。**不是 pkg-config**，所以 Conan 依赖必须
  以路径前缀注入（R49：指向包目录，绝不指向 /usr/local）。
- 无平台三元组探测（无 config.guess/config.sub），所以 E007 类补丁对它
  无从谈起——OHOS 工具链完全通过 profile 的 `CC`/`CFLAGS` 进入。
- `Makefile.am` 仅 `bin_PROGRAMS = memcacheq`，`make install` 只装这个
  可执行文件；`--enable-threads` 打开 pthread 路径。

## 3. 适配过程中的问题与解法

| # | 问题 | 解法 | 沉淀 |
|---|------|------|------|
| 1 | tarball `configure`/`config.status` 用 `umask 077 && mktemp -d ./confXXXXXX` 建临时目录；HMDFS 上产出 `drwx--S--- file_manager`，**属主自己都不可写**，configure 与 config.status 全部 `Permission denied`（E012） | 配方内改写：`umask 077 → 022`，mktemp 重定向到 build 目录下私有 `confstat/`；configure 生成 config.status 后再对其做同样改写（`make` 会在依赖新时重跑它） | notes/manifest 已记；与 memcached 的 $TMPDIR 问题同族但机理不同（umask+setgid vs 只读 /tmp） |
| 2 | conanbuildenv 硬编码 `SHELL=/data/service/hnp/bin/bash`（仅 CI worker 存在）；configure 把它写进 config.status 的 shebang，dev box 上后续 `make` 重跑 config.status 即挂 | 配方探测真实可用的 bash（CONFIG_SHELL → usr/local/bin/bash → /bin/sh），并在 `. conanbuild.sh` 之后**重新 export** `SHELL`/`CONFIG_SHELL` | manifest knowledge_gained |
| 3 | `hashtable.h` 的 `extern inline` 是 GNU89 语义；profile cppstd=gnu20 下 clang 拒绝 hashtable.c 的非 inline 定义（`redefinition of 'extern inline' function is not supported in C99 mode`） | CFLAGS 注入 `-fgnu89-inline`，零源码补丁 | manifest knowledge_gained |
| 4 | basic_layout 下 build 文件夹在 source export **内部**，`copytree(source → build/work)` 自嵌套无限递归 | `ignore_patterns(<build-dir-name>, "conan")` | manifest knowledge_gained |
| 5 | 二进制运行时 musl loader 找不到 `libevent-2.1.so.7`/`libdb-6.2.so`（无 RPATH 是刻意设计，A5 校验项） | ①配方 `package_info()` 里 `runenv_info.append("LD_LIBRARY_PATH", <dep lib>)`（conan 正统传递方式）；②test_package 显式 re-quire 两个依赖拿到真实 package_folder，在 `self.run` 命令行前缀注入 LD_LIBRARY_PATH（`env="conanrun"` 会丢弃 os.environ 的改动） | manifest knowledge_gained |
| 6 | Conan 2 中 test_package 的**传递依赖**（memcacheq 之下的 libevent/db）在消费图里 `package_folder=None`，无法定位其 lib/ | 见上：test_package 显式 requires 同版本依赖 | manifest knowledge_gained |
| 7 | `-pr` 同时作 host+build profile 时 build_os=Linux ≠ host_os=OHOS → `can_run()`=False，本机（本身就是 OHOS 原生机）功能层被误跳过 | 本机验证加 `-c tools.build.cross_building:can_run=True`；CI 的 `-pr:h/-pr:b` 均为 ohos-aarch64（build_os=OHOS）不受影响 | 验证命令已记 manifest |

## 4. 上游测试审计（结论：**无上游测试**）

对官方 tarball（30 个文件）逐项审计：

- `Makefile.am`/`Makefile.in`：无 `check`/`test` 目标（仅 `bin_PROGRAMS`、
  `EXTRA_DIST = tools AUTHORS LICENSE run.sh`）。
- `configure.ac`：无任何测试框架探测（无 check/criterion/gtest/CUnit）。
- `tools/`：仅 3 个文件——`memcache.py`（memcached 客户端库副本）、
  `mqpush.py`/`mqpop.py`（交互式演示脚本，无断言、无期望输出）。
- 无 CI 配置（无 .github/workflows、.travis.yml）。
- `run.sh` 是启动示例脚本，非测试。

→ 按 no_tests 处理，全部测试覆盖由 test_package 补全（见
`test_package/MANIFEST.yml` 审计表）。

## 5. 测试设计（双层，22 项）

### 5.1 鸿蒙特有层 A1–A7（`ohos_abi_check.py`，纯 Python ELF 检查）

| 项 | 断言 |
|----|------|
| A1 | ELF64 LE、e_machine=EM_AARCH64 |
| A2 | PT_INTERP=`/lib/ld-musl-aarch64.so.1`（OHOS musl loader，非 glibc） |
| A3 | `.note.ohos.ident` owner=OHOS（OHOS clang/lld 特有） |
| A4 | DT_NEEDED 恰为 `libc.so` + `libevent-2.1.so.7` + `libdb-6.2.so`（musl 无版本化系统 soname；libevent/libdb 的版本号是上游自身命名，非 glibc 符号版本化） |
| A5 | 无 DT_RPATH/DT_RUNPATH（不携带构建机路径） |
| A6 | PIE + PT_GNU_RELRO + 不可执行 GNU_STACK + BIND_NOW（HNP 加固基线） |
| A7 | 无 GLIBC_* 符号版本需求、无 .note.ABI-tag（musl/OHOS 产物特征） |

刻意**不**断言 `.codesign` 段：签名只在有 HNP 签名工具的 worker 上发生
（E077），跨端断言任一方向都不可复现。脚本不依赖任何外部工具，纯
Python 解析 ELF，在无法执行 OHOS ELF 的 dev box 上同样可跑——这正是它
存在的意义（CI L1e 反向破坏检查在交叉构建时也有效）。

### 5.2 功能层 F1–F13b（`test_memcacheq.sh`，对打包产物跑真守护进程）

启动**包目录里**的 `memcacheq`（`-p <随机端口> -H <临时 dbhome> -N -R -v`），
用 toybox netcat（`-w/-q`，无 `-z`，已适配）以 memcache 协议驱动 15 个
独立断言：version、set→STORED、get→VALUE、空队列→END、双消息 FIFO 顺序、
stats pid、stats queue、delete→NOT_FOUND、未知命令→ERROR、长度校验、
双队列隔离×2、`-h` usage、`-i` license。

### 5.3 计数口径

22 = 功能 15（F1–F13b）+ 鸿蒙特有 7（A1–A7），与 `test_package/MANIFEST.yml`
及 PR 申报表一致。

## 6. 验证记录（本机 HarmonyOS aarch64 原生）

```
conan create . --user=ohpcd --channel=stable --build=missing \
  -pr ~/.conan2/profiles/ohos-local \
  -c tools.build.cross_building:can_run=True
→ memcacheq/0.2.1@ohpcd/stable: Package '08296a62e5c8954c01832a8b7918e686' created
→ OHOS_ABI_CHECK={"discovered": 7, "passed": 7, "failed": 0}
→ # total=15 passed=15 failed=0   （F1–F13b）
→ test_package 完成，conan create 退出码 0
```

Debug 配置本机受限：`db/6.2.32` Debug 需从源码构建，其 configure shebang
要求 `/data/service/hnp/bin/bash`（仅 CI worker 存在）→ **被依赖包的
dev-box 限制阻塞，与 memcacheq 配方无关**；memcacheq 自身无 build_type
条件逻辑，CI（ohos-aarch64 profile）跑双配置。

## 7. 知识沉淀评估

问题 1、2、5、6 均为**通用 HarmonyOS/Conan 适配问题**（HMDFS umask 特性、
CI 路径硬编码、musl loader 与包目录、test_package 传递依赖缺陷），已写入
manifest.yaml `knowledge_gained` 与本 notes。其中 1/2/5/6 是对既有 E012/
memcached 先例的**新变体**（机理细化：umask+setgid 而非只读 /tmp；
conanbuildenv SHELL 污染链路），但都属于既有知识条目的延伸而非全新类
别，暂不单独扩张知识库条目；若后续还有包踩 `SHELL=/data/service/hnp/bin/bash`
这个坑，建议合并成一条独立知识（本 notes 先行记录）。

## 8. 后续

- [ ] CI 双配置（Release/Debug）跑通后回填 verification 字段
- [ ] PR 申报表（上游 0 / 补全 22）
