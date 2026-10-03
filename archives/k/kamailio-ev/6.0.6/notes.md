# kamailio-ev 6.0.6 适配笔记 — HarmonyOS PC / aarch64

## 1. 概况

| 项 | 值 |
|----|----|
| 库名 / 版本 | kamailio-ev / 6.0.6 |
| 上游仓库 | https://github.com/kamailio/kamailio（官网 https://www.kamailio.org） |
| 适配路径 | `archives/k/kamailio-ev/6.0.6/` |
| 许可证 | GPL-2.0-or-later |
| 语言 | C（上游 evapi 模块全为 C 源，无 C++ 源文件） |
| 构建系统 | kamailio 经典 Makefile 体系（`src/Makefile` + `Makefile.defs`），非 CMake/autotools |
| 打包口径 | 仅打包 Alpine `main/kamailio` APKBUILD 的 `kamailio-ev` 子包对应模块：`_mod_list_ev="evapi"` |
| 产物 | `lib/kamailio/modules/evapi.so`（1 个 core 插件模块） |
| 外部依赖 | `libev/4.33`（制品仓已发布，无传递依赖） |
| 补丁数 | **0**（`conandata.yml` 中 `patches: {}`） |
| 源码 | 官方 `kamailio-6.0.6_src.tar.gz`，sha256 `32e4290c6813c9d0289abe9ec2de9138e12e0381179218a7fed374ad813ecc48` |
| 使用知识库条目 | E525（OHOS SELinux 禁 FIFO → make 统一 `-j1`）、E074、同族先例 kamailio-{tls,gcrypt,xml,unixodbc,extras} |

模块职责：把基于 **libev** 的网络事件广播接口暴露给 kamailio 配置脚本
（`evapi_relay*`/`evapi_unicast*`/`evapi_multicast*`/`evapi_close`/`evapi_set_tag`）
与 KEMI 路由脚本（`KSR.evapi.*`），并向外部 TCP 客户端推送/接收事件消息。
源码目录 `src/modules/evapi/`：`evapi_mod.c`（模块入口）、`evapi_dispatch.c`（事件循环 +
连接/队列管理）、`evapi_dispatch.h`、`Makefile`、`CMakeLists.txt`、`doc/`、`README`。

### 1.1 依赖发布状态（R36 / W0：适配前先查依赖）

| 依赖 | 制品仓状态 | 证据 |
|------|-----------|------|
| libev/4.33 | ✅ 已发布（recipe rev `5ff7c6c5aa4bbead1a8ac706df56d6bc`，2026-07-27；binary `01d92cf349a0dd98ff915f4bd99a04430171517f`） | `conan download libev/4.33 -r=ohpcd --only-recipe` → rc=0；`conan download 'libev/4.33:*' -r=ohpcd -p "os=OHOS AND arch=armv8 AND compiler=clang"` → rc=0（`Package installed`，settings 命中 os=OHOS/os.version=6.0/arch=armv8/clang15/libc++/cppstd17/Release/shared=True） |

`conan graph info --requires=libev/4.33` 显示 `dependencies={}` → 无传递第三方依赖。
→ 无缺失依赖，本任务**不需要**新建依赖项分支（CI 不会落回 `--build=missing` 源码构建）。

## 2. 打包范围（1 个模块）

| 模块 | 上游源（`src/modules/`） | 产物 | 模块级外部依赖 |
|------|------------------------|------|---------------|
| evapi | `evapi/evapi_mod.c`、`evapi_dispatch.c` | `lib/kamailio/modules/evapi.so` | `libev`（`-lev`，经模块 Makefile 的 `pkg-config --exists libev` 探测，见 §4.3） |

不打包 kamailio 主程序（与本仓同族 12 个 `kamailio-*` 配方一致：模块 .so 由 kamailio
运行时 `loadmodule` 加载，模块包不依赖 kamailio 本体包）。

## 3. 构建方法

配方 `conanfile.py` 的 `build()` 实际执行（等价于手工两步）：

```bash
# 1) 生成 src/config.mak（必须先 cfg，否则 make 报 No rule to make target 'cfg-defs'）
make cfg include_modules="evapi" \
     extra_defs="-D_GNU_SOURCE -DHAVE_GETHOSTBYNAME2 …" \
     BUILDER= LOCALBASE=<libev 包目录>

# 2) 编模块（-j1 见 §4.5）
make modules modules="modules/evapi" -j1 \
     extra_defs="…" BUILDER= LOCALBASE=<libev 包目录>
```

编译器与依赖路径经 Conan `Environment` 显式注入（R33，不裸用 `${CC}`/`${CFLAGS}`）：
`CC` ← `tools.build:compiler_executables`（`/data/service/hnp/bin/clang`）；
`CPATH` ← `<libev>/include`；`LIBRARY_PATH` ← `<libev>/lib`。

实际链接行（`make -n` 原始输出，证据 `evidence/logs/manual-build-1.log` 与
`evidence/logs/builder-pin-experiment.log`）：

```
/data/service/hnp/bin/clang -shared -g -pthread -Wl,-O2 -Wl,-E -rdynamic "-ldl" \
  -Wl,-Bsymbolic-functions evapi_dispatch.o evapi_mod.o -lm \
  -L<libev 包目录>/lib -L/lib -lev -o evapi.so
```

（`-L/lib` 来自 `SYSBASE` 未定义时空串展开，见 §7 已知限制 3。）

## 4. 平台差异与解决（全部经 make 命令行变量表达 → 0 补丁）

### 4.1 平台探测宏缺失（`OS=harmonyos` 不在 `Makefile.defs` 平台分支内）

`Makefile.defs` 只处理 linux/solaris/freebsd/darwin 分支，OHOS 命中不了任何 `HAVE_*`
探测宏，模块源码中的条件编译会走错分支（core 头 `resolve.h`/`sched_yield.h` 直接
`#error`）。解决：经 make 命令行变量 `extra_defs` 注入 linux 分支等价宏集（9 项，见
`conanfile.py` 的 `PLATFORM_DEFS`），与同族 kamailio-tls/gcrypt/xml/extras 先例逐项
一致（宏集已对照 OHOS SDK musl 语义 sysroot 实证存在）。**未改任何上游文件，故 0 补丁。**

### 4.2 只编模块、不编 core（0 补丁的关键）

kamailio 主程序（core）在 OHOS 上有两处 musl 头文件差异会导致编译失败：
`core/resolve.c` 的 `HAVE_RESOLV_RES` → `_res`、`core/lock_ops.h` 的
`HAVE_UNION_SEMUN` → `union semun`。这两条路径**只在编译 kamailio 主程序时触发**；
本配方只编 `modules/evapi`，不触碰 → 无需任何补丁。模块运行期所需 core 符号由
kamailio 主程序在 `loadmodule` 时提供（本包实测 56 个 core 未定义符号，见 §6.2）。

### 4.3 libev 依赖探测钉死（本模块特有，变量名是裸 `BUILDER`）

`src/modules/evapi/Makefile` 的探测逻辑原文：

```make
ifeq ($(CROSS_COMPILE),)
	BUILDER = $(shell which pkg-config)
ifneq ($(BUILDER),)
	PKGLIBUV = $(shell $(BUILDER) --exists libev > /dev/null 2>&1 ; echo $$? )
ifneq ($(PKGLIBUV),0)
	BUILDER =
endif
endif
endif
ifneq ($(BUILDER),)
	DEFS += $(shell $(BUILDER) --cflags libev)
	LIBS += $(shell $(BUILDER) --libs libev)
else
	DEFS += -I$(LOCALBASE)/include -I$(SYSBASE)/include
	LIBS += -L$(LOCALBASE)/lib -L$(SYSBASE)/lib -lev
endif
```

三条本模块必须注意的事实（与 tls/gcrypt 不同）：

1. **变量名是裸 `BUILDER`**（tls 用 `SSL_BUILDER`、gcrypt 用 `GCRYPT_BUILDER`）——
   钉死手法必须逐模块核对 Makefile 原文，不能套用同族其它配方的变量名。
2. conan 制品仓的 `libev/4.33` **不携带 `.pc` 文件**（包内仅 `include/ev.h`、
   `include/ev++.h`、`include/event.h`、`lib/libev.so`），因此 `pkg-config --exists libev`
   在"干净"构建机上必然失败 → 模块 Makefile 自动清空 `BUILDER` 回退 LOCALBASE。
3. 但若构建机装有**同名系统库**（带 libev.pc），探测会命中并指向构建机路径 —— 交叉
   编译事故源。故配方显式传 `BUILDER=`（make 命令行变量优先于 Makefile 文件内赋值），
   跳过探测分支、确定性走 LOCALBASE 回退；`LOCALBASE` 指向 conan libev 包目录，
   `CPATH`/`LIBRARY_PATH` 兜底（pkg-config 缺失时仍可编译/链接）。

**实测证据**（`evidence/logs/builder-pin-experiment.log`，把返回 `-I/FAKE_HIJACK/include
-L/FAKE_HIJACK/lib -lev` 的假 `pkg-config` 前置进 PATH，模拟"构建机有系统 libev"）：

| 实验 | 链接行实得 | 判定 |
|------|-----------|------|
| A：不传 `BUILDER=` | `-L/FAKE_HIJACK/lib -lev` | ❌ 被构建机 pkg-config **劫持** |
| B：传 `BUILDER=` | `-L<libev 包>/lib -L/lib -lev` | ✅ 钉死到 conan 依赖包 |

> 反向核验：本机 `pkg-config --exists libev` 为"未找到"（无系统 libev.pc），
> 故未钉死时亦回退 LOCALBASE —— 即**同一命令在不同构建机上有两种落点**，这正是必须
> 显式钉死的原因。

### 4.4 模块 .so 的外部动态依赖语义（实测依赖形态）

`evapi.so` 的 `DT_NEEDED` = `{libc.so, libev.so}`（实测，见 §6.2）。libev 在 OHOS
sysroot 与目标机 `/lib` 中**不是**系统同名库（无 `libev.so*`），故不落入 R26「系统同名
库须静态」的适用范围，按仓库口径由 conan 依赖链提供运行时 .so；模块自身**无
RPATH/RUNPATH**（实测），部署时经 `LD_LIBRARY_PATH`（或等价加载路径）定位 `libev.so`，
与同族 gcrypt（动态 libgcrypt）、cnxcc（动态 libevent）判例一致。
`package_info()` 中 `libdirs = ["lib/kamailio/modules"]`、`libs = []`（模块不被链接消费）。

补充实测：libev/4.33 的 `libev.so` **无 SONAME**（`readelf -d` 无 SONAME 条目），
故链接时 `-lev` 记录的 `DT_NEEDED` 即字面名 `libev.so`，与包内文件名逐字一致——
运行时按名查找可直接命中，无需 `.so.N` 版本链。

### 4.5 统一 `-j1`（E525/E074）

OHOS SELinux 禁止用户进程创建 FIFO，而 GNU make jobserver 依赖 FIFO 传递令牌，
`-j>1` 存在挂起/报错风险 → 全流程 `-j1`，与同族 kamailio-* 配方一致。

## 5. 上游测试（R51 三步法）

### 5.1 清点（源码包实测全量；证据 `evidence/logs/upstream-test-inventory.log`）

官方源码包 `kamailio-6.0.6_src.tar.gz`（sha256 `32e4290c…`）内：

- **顶层 `test/` 目录：0 个**（6.0.6 的 `_src` 发布包不含独立 `test/` 目录，与 git 仓库不同）
- 分散的 `test`/`tests` 目录共 **4 个**、文件共 **17 个**：

| 目录 | 文件数 | 性质 |
|------|-------|------|
| `utils/kamctl/dbtextdb/tests/` | 10 | 数据文件（由同目录 `dbtextdb_test.py` 消费） |
| `src/modules/janssonrpcc/test/` | 3 | jsonrpc-c 模块脚本 + 配置（非本包模块） |
| `src/modules/rtpproxy/test/` | 3 | rtpproxy 模块配置 + 命令行记录（非本包模块） |
| `src/modules/tm/test/` | 1 | tm 模块开发期 IPC 清理脚本（非本包模块） |

- **evapi 模块自身无上游测试**：`find src/modules/evapi -name '*test*'` → 空；
  `src/modules/evapi/CMakeLists.txt` 无 `add_test`/`enable_testing`；
  `src/Makefile` 与模块 Makefile 均无 `check` 目标。
- 另清点出 3 个 `src/modules/xmlrpc/examples/` 手工联调客户端（非 test/tests 目录但
  属可执行入口，已在 MANIFEST.yml 逐项登记未执行原因）。

### 5.2 实测运行（可运行环境：OHOS aarch64 构建环境）

17 个文件中**唯一自包含、不需要运行中 kamailio 实例**的上游测试是
`utils/kamctl/dbtextdb/dbtextdb_test.py`（上游自带 unittest 入口，3 个用例，仅依赖
Python 标准库）。已在 `conanfile.py` 的 `build()` 末尾真实执行（CI 每次构建都会跑）：

```
$ python3 dbtextdb_test.py -v
testExecute (__main__.DBTextTest.testExecute) ... ok
testOpenTable (__main__.DBTextTest.testOpenTable) ... ok
testParseQuery (__main__.DBTextTest.testParseQuery) ... ok
----------------------------------------------------------------------
Ran 3 tests in 0.014s

OK
rc=0
```

→ 上游可运行测试 **总数 3 / 通过 3 / 失败 0 / 跳过 0，通过率 100%**。
逐项名称：`testParseQuery`、`testOpenTable`、`testExecute`。
（上示 `Ran 3 tests in 0.014s` 取自 `conan create` 内执行；探索环境独立运行为 `0.096s`、
本地 CI 模拟为 `0.015s` —— 耗时读数随环境波动，用例数/通过数/结果三处一致，不作为断言。）
日志：探索期独立日志 `evidence/logs/upstream-dbtextdb_test.log`；`conan create` 内日志
`evidence/logs/conan-create-1.log`（CI 中为该次构建日志）。

### 5.3 未执行项逐项原因（非「没环境」，均为具体技术原因）

| 文件 | 未执行原因 |
|------|-----------|
| `tests/` 下 10 个数据文件 | 纯数据（无执行位、无断言），由已执行的 `dbtextdb_test.py` 读取消费 |
| `janssonrpcc/test/run-tests.sh` | 需同源码树构建的 kamailio **主程序** + 该模块 loadmodule 运行实例；本包产物仅 `evapi.so`（同族口径不构建 core） |
| `janssonrpcc/test/mem-test.sh` | 同上，另需 `valgrind`（OHOS 无该工具链） |
| `janssonrpcc/test/test.cfg` | 配置文件，无执行入口 |
| `rtpproxy/test/kamailio.cfg` | 配置样例，需运行中 kamailio + 外部 rtpproxy 进程 |
| `rtpproxy/test/exec_{rtpproxy,pjsua}.txt` | 纯文本命令行记录（无执行位、无断言），pjsua 为外部二进制 |
| `tm/test/kill_sem.sh` | 非测试用例：需 root，且 `ipcrm` 会删除构建机**全部** SysV IPC 对象，在共享 CI worker 上会破坏其他进程；上游仅作开发调试清理用 |
| `xmlrpc/examples/xmlrpc_test.py` / `xmlrpc_test2.py` | Python 2 专属（`import xmlrpclib, httplib`，Python 3 无此模块）且需连接运行中的 kamailio XMLRPC 端口；属 xmlrpc 模块示例 |
| `xmlrpc/examples/xmlrpc_test.pl` | 需运行中 kamailio + Perl XMLRPC 依赖；属 xmlrpc 模块示例 |

## 6. 适配后测试（鸿蒙特有，`test_package/`）

| 用例 | 内容 | 实测结果 |
|------|------|---------|
| `check_evapi_module.py` | 纯 Python ELF 自解析：ELF 身份、模块契约名 `exports->name == "evapi"`、30 个契约导出符号、`DT_NEEDED == {libc.so, libev.so}`、无 RPATH/RUNPATH、97 个未定义符号 100% 归类（libc/CRT 37 + libev 4 + kamailio core 56）、依赖包逐符号核验 `ev_*`、libev.so 自身 `DT_NEEDED ⊆ {libc.so}` 且同为 aarch64 ET_DYN 且无 RPATH、许可证随包 | **17/17 通过** |
| `test_evapi_e2e.c` | 鸿蒙特有端到端消费者用例（rule12，详见 §6.3） | **134/134 断言通过** |
| `kamailio_core_stub.{c,h}` | core 符号最小层（56 个符号；类型逐字段对齐上游头文件，见 §6.2） | 随 e2e 编译并通过，`-Wl,--export-dynamic` 导出符号 |

> test_package 不替代上游测试统计：上游统计见 §5（3/3 真实执行）。

### 6.1 e2e 用例覆盖的加载路径（rule12 完整消费者用例）

```
dlopen(evapi.so, RTLD_NOW|RTLD_GLOBAL)      ← musl 不做惰性绑定，全部符号须可解析
  → dlsym("exports")                         ← module_exports：name/dlflags/rpcs/cmds/params/pvs
      校验：name=="evapi"、dlflags==DEFAULT_DLFLAGS 哨兵 0、rpcs==0
            cfg 命令表 9 项（名称 + 参数个数 1/1/2/2/2/2/0/1/1；evapi_close 两个重载 fixup=NULL）
            参数表 7 项（名称 + 绑定目标指针 == 模块内真实全局量 + 默认值
                          workers=1/max_clients=8/wait_idle=500000/wait_increase=3/dispatcher_pid=-1）
            PV 表 1 项（$evapi，type==PVT_OTHER(22)，getf/setf/parse_name 非空）
  → dlsym("mod_register") + 调用               ← 加载器随后调用的注册入口
      → 观察 core 侧 sr_kemi_modules_add()：恰调用 1 次，取得 8 项 KEMI 表
        （子模块名 evapi；relay/relay_unicast/relay_multicast/close/set_tag/
          async_relay/async_unicast/async_multicast；rtype==SR_KEMIP_INT；ptypes str/str 序列）
  → 真实调用模块导出函数
      evapi_env_reset()          环境结构复位（conidx=-1，其余字段清零；NULL 契约不崩溃）
      evapi_init_environment(1)  桩层记录恰好解析 3 个事件路由：
                                 evapi:connection-new / evapi:connection-closed /
                                 evapi:message-received（route_lookup 收到 &event_rt 非空）
      evapi_set_tag()/evapi_cfg_close()  NULL 分支返回 -1
      核心运行期入口符号齐备：clients_init/queue_init/run_dispatcher/run_worker/relay×3
  → 真实调用运行时依赖 libev（模块 DT_NEEDED=libev.so）
      ev_default_loop() + ev_io_start() + ev_run() + ev_io_stop()
      → 管道可读事件回调真实触发（libev 在目标机可加载且可运行）
  → dlclose
```

### 6.2 core 符号桩层的类型对齐（沿用 gcrypt 先例教训）

`evapi.so` 实测 **97** 个未定义符号：libc/CRT **37**（含 4 个 weak CRT）、
libev **4**（`ev_default_loop`/`ev_io_start`/`ev_io_stop`/`ev_run`）、
kamailio core **56**（桩层提供）。类型逐字段对齐上游头文件（证据
`evidence/logs/undef-symbol-decls.log` —— 逐符号检索 `src/core/` 声明的原始输出）：

| 符号 | 上游声明（6.0.6） | 桩层形态 |
|------|------------------|---------|
| `my_pid` | `dprint.h:161` `int my_pid(void)` | **函数**（非变量） |
| `dprint_color` / `dprint_color_reset` | `dprint.h:217-218` | 函数 |
| `log_level_info` | `dprint.h:203` `struct log_level_info[]` | 数组，字段序 `{char *name; int syslog_level;}` |
| `log_prefix_val` | `dprint.h:169` `str *` | 指针 |
| `_km_log_func` / `_ksr_slog_func` | `dprint.h:155/175` | 函数指针，指向**非空 sink** |
| `event_rt` | `route.h:94` `struct route_list` | 对象（`{struct action **rlist; int idx; int entries; struct str_hash_table names;}`） |
| `route_lookup` | `route.h:102` `int route_lookup(struct route_list *rt, char *name)` | 真实实现：记录调用与路由名，恒返回 -1 |
| `sr_kemi_modules_add` | `kemi.h:558` `int sr_kemi_modules_add(sr_kemi_t *klist)` | 真实实现：记录表指针并计数 |
| `_shm_root` | `mem/shm.h:46` `sr_shm_api_t`（**对象**，非指针） | 等尺寸结构体对象 |
| `cfg_*` 9 个 | `cfg/cfg_struct.h:186-196`（3 个函数 + 6 个数据） | 按声明形态分函数/数据 |

**类型对齐 + 非空日志 sink** 是 gcrypt 先例用 SIGSEGV 换来的教训：桩层类型错位时
模块 `LM_ERR` 日志路径会解引用野指针，崩溃会掩盖真实失败原因。本用例的
`get_debug_level()` 返回 0（低于所有级别）使模块日志静默，同时日志函数指针仍指向
sink —— 双保险。

### 6.3 鸿蒙特有用例计数

| 用例 | 断言数 | 鸿蒙相关性 |
|------|-------|-----------|
| OHOS 加载器同源 dlopen 路径（RTLD_NOW 全符号解析 + core 桩层） | 134（其中加载路径段 128） | OHOS/musl 不做惰性绑定 → 必须复现 RTLD_NOW 语义 |
| libev 运行时依赖在 OHOS 上可加载且可运行 | 5 | libev 非系统同名库，由 conan 依赖链提供，须实证可加载 |

→ 鸿蒙特有测试用例数 **2（≥1 达标）**。

## 7. 验证证据（W3：本地 OHOS aarch64 `conan create`）

命令（与 CI `build_and_test.sh:1364` 同源形态：显式 profile + 只从源码构建被测包）：

```bash
conan create . -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 \
               -pr:b=<repo>/ci/conan/profiles/ohos-aarch64 --build="kamailio-ev/*"
```

关键输出（完整日志 `evidence/logs/conan-create-1.log`）：

```
kamailio-ev/6.0.6: Calling build()
testExecute (__main__.DBTextTest.testExecute) ... ok        ← 上游 dbtextdb 3/3
testOpenTable (__main__.DBTextTest.testOpenTable) ... ok
testParseQuery (__main__.DBTextTest.testParseQuery) ... ok
Ran 3 tests in 0.014s
kamailio-ev/6.0.6: package(): Packaged 1 file: COPYING
kamailio-ev/6.0.6: package(): Packaged 1 '.so' file: evapi.so
======== Testing the package: Executing test ========
… check_evapi_module.py：17 项 [ok]（0 FAIL）
ALL CHECKS PASSED (134/134)
ALL OHOS E2E PASSED (134 assertions, loadmodule path dlopen->exports->cmds/params/pvs->
  mod_register->KEMI table->env_reset/init_environment/set_tag->libev io callback->dlclose)
### rc=0
```

关键实测事实（`check_evapi_module.py` 断言 + `readelf`/`nm` 交叉核验）：

| 项 | 实测值 |
|----|--------|
| ELF 身份 | ELF64 LSB、`ET_DYN`、`EM_AARCH64` |
| 模块契约名 | `exports->name == "evapi"`（module_exports 首字段） |
| `exports.dlflags` | `0`（DEFAULT_DLFLAGS 哨兵值，交回 core 决定实际 dlopen flags） |
| cfg 命令表 | 9 项（evapi_relay/evapi_async_relay/evapi_multicast/evapi_async_multicast/evapi_unicast/evapi_async_unicast/evapi_close×2/evapi_set_tag） |
| 参数表 | 7 项（workers/bind_addr/netstring_format/event_callback/max_clients/wait_idle/wait_increase） |
| KEMI 函数表 | 8 项，子模块名 `evapi`，返回类型均 `SR_KEMIP_INT` |
| `DT_NEEDED` | `{libc.so, libev.so}`（无其他） |
| `RPATH`/`RUNPATH` | 无（部署经 `LD_LIBRARY_PATH` 定位依赖链） |
| 未定义符号 | 97 个，100% 归类：libc/CRT 37 + libev 4 + kamailio core 56 |
| 依赖链闭合 | `libev.so` 在 conan 依赖包内实测存在；被引用的 4 个 `ev_*` 逐符号核验由该包导出；`libev.so` 自身 `DT_NEEDED == {libc.so}` |
| 许可证 | `licenses/COPYING`（GPL-2.0-or-later）随包 |

## 8. 已知限制与未覆盖项（如实登记）

1. **运行时依赖不在包内**：`evapi.so` 的 `DT_NEEDED` 含 `libev.so`（非系统同名库），
   该 .so 由 conan 依赖链（`libev/4.33`）提供，部署时须使目标机可达该库
   （`LD_LIBRARY_PATH` 或等价机制）。本仓库同族 gcrypt（动态 libgcrypt）、
   cnxcc（动态 libevent）同判例。
2. **不构建 kamailio core**（同族 12 个 `kamailio-*` 配方一致口径）：本包不含 kamailio
   主程序，故无法在本包内做「真实 kamailio 进程 loadmodule 后跑 cfg/KEMI 脚本收发事件」
   级验证；e2e 以 core 符号桩层（`kamailio_core_stub.c`）加载同一 `evapi.so`，真实调用
   模块导出函数与 KEMI 注册路径，作为消费者路径的等价验证。
3. **链接行含 `-L/lib`**：模块 Makefile 回退分支含 `-L$(SYSBASE)/lib`，而 `SYSBASE` 在
   `Makefile.defs` 中未定义 → 空串展开为 `-L/lib`。在本机（OHOS aarch64）`/lib` 不含
   libev，故不影响结果；同族 kamailio-* 配方均有同一形态（非本配方引入）。若将来某构建机
   `/lib` 出现同名库，需显式传 `SYSBASE=<空/受控路径>` —— 已登记为可改进项（未改动以保持
   与同族配方逐字一致）。
4. **连接/队列路径未做运行期用例**：`evapi_queue_init/evapi_queue_add/evapi_queue_get`
   与客户端连接路径依赖 kamailio core 的共享内存池（`_shm_root`，需实现 core 的 shm
   分配器）与 core 锁集（`_atomic_lock_set`），桩层复现成本高于收益，故只核验符号齐备
   （`dlsym` 非空）而不调用；上游亦无该模块测试用例。
5. **evapi 模块无上游自动化测试**（§5.1 清点证据）：本包上游测试统计来自源码包内唯一
   自包含的 unittest（dbtextdb，3/3）。
6. **不做平台功能裁剪**：模块的 cfg/KEMI 导出面与上游一致，未 stub 任何功能。
7. **`-g` 保留 + 未 strip**：产物带调试信息，且 `.debug_*` 段记录了构建期依赖头文件路径
   （strings 命中 `<conan cache>/p/libev*/p/include/ev.h`）。该路径仅存在于 DWARF 调试段，
   不参与运行期加载（模块源码未引用 `CFG_DIR`/`SHARE_DIR`/`RUN_DIR` 宏，已核验）；与
   同族 kamailio-* 产物形态一致。

## 9. 拟沉淀知识（供知识图谱收录）

本次适配产生一条**共性问题**知识（非本库专属补丁），已按 R19 先草稿后审核的流程落盘
`knowledge/drafts/`（kv + md 一一对应）：

| 草稿 | 共性问题 | 检测手段 | 处理策略 |
|------|---------|---------|---------|
| `kamailio-ev-6.0.6-module-pkgconfig-probe-pinning` | kamailio 模块 Makefile 以 `<模块专属变量名>` + pkg-config 探测外部依赖，**变量名逐模块不同**（`SSL_BUILDER`/`GCRYPT_BUILDER`/裸 `BUILDER`/…），探测失败才会回退 LOCALBASE；同一命令在不同构建机上因此有**两种落点**，构建机同名系统库会劫持链接（交叉编译事故） | `make -n` 打印实际编译/链接行，检查依赖包路径是否出现；PATH 前置假 `pkg-config` 做劫持实验（本次实测：不钉死 → `-L/FAKE_HIJACK/lib`，钉死 → 依赖包路径） | 取模块 Makefile 原文确认**变量名**，再以 make 命令行变量显式钉死（依赖包无 .pc 时直接置空以跳过探测分支），配合 `LOCALBASE`/`CPATH`/`LIBRARY_PATH` 三处指向依赖包 |

## 10. 文件清单

```
archives/k/kamailio-ev/
├── manifest.yaml                 # 软件级元数据 + 版本索引
├── README.md                     # 软件描述
└── 6.0.6/
    ├── conanfile.py              # 单模块配方（0 补丁；R33 显式注入 CC/CPATH/LIBRARY_PATH）
    ├── conandata.yml             # 官方源码 URL + sha256（patches: {}）
    ├── manifest.yaml             # 版本级编译元数据（状态/证据/依赖）
    ├── notes.md                  # 本文件
    └── test_package/
        ├── conanfile.py          # 消费者测试驱动（check 脚本 + e2e 编译/运行）
        ├── check_evapi_module.py # 产物结构/依赖闭包断言（17 项，纯 Python ELF 解析）
        ├── test_evapi_e2e.c      # 端到端消费者用例（134 项断言，含真实 libev 回调）
        ├── kamailio_core_stub.c  # core 符号最小层（56 符号，类型对齐上游头文件）
        ├── kamailio_core_stub.h
        └── MANIFEST.yml          # 上游测试清点/实跑台账 + 鸿蒙特有测试登记
```

### 对话 #1 — 适配路径确定与验证（关键决策与教训）

1. **先跑通再固化**：手工构建（`evidence/build-manual.sh`）一次通过（rc=0），
   但 e2e 用例首版有 1 处预期表错误（`evapi_close` 第二个重载参数个数写成 0，实为 1），
   在探索环境跑出 `ASSERT FAILED [32]` 后修正 —— 若直接进 `conan create`，会在 CI 里
   浪费一轮。**结论：test_package 先在探索环境实跑，再进配方。**
2. **预期断言必须来自上游源码原文**：cfg 命令表参数个数、参数表绑定目标、KEMI 表
   ptypes 均逐项抄自 `evapi_mod.c` 原文，而非凭经验推断（第 1 条的错即来自"两个 close
   重载参数个数相同"的错误直觉）。
3. **依赖探测变量名不可套用同族配方**：tls 的 `SSL_BUILDER`、gcrypt 的
   `GCRYPT_BUILDER` 都带模块前缀，evapi 却是裸 `BUILDER` —— 必须读模块 Makefile 原文。
   同时 evapi/Makefile 有"探测失败自动清空 `BUILDER`"的分支，使"能否消费依赖 .pc"
   成为链路落点的隐藏开关（libev/4.33 无 .pc）。
4. **钉死手法要可证伪**：用假 `pkg-config` 前置 PATH 做 A/B 实验，把"应该能挡住劫持"
   变成"实测挡住 / 未挡住有原始输出"，而不是注释里的一句声明。
5. **TMPDIR 显式提供**：鸿蒙目标机 `/tmp` 只读，test_package 编译 e2e 时若沿用环境
   `TMPDIR`，clang 会直接报 `unable to make temporary file`。已在 `test_package/conanfile.py`
   中显式提供可写临时目录（既有 `TMPDIR` 可写则沿用，否则退到 build 目录下 `tmp/`）。
6. **依赖零缺口**：`libev/4.33` 制品仓已发布（`conan download` recipe 与 binary 均 rc=0），
   故本任务不需要新建依赖项分支；`conan create` 按 CI 形态只 `--build="kamailio-ev/*"`，
   不给依赖留源码构建的口子（R36）。
---

**编译结束**: 2026-10-02 14:03
**最终状态**: built（R29 口径：conan create / conan-verify 已全部 PASS，但尚未 `conan upload` 到制品仓 → 真实状态为 built；合并后经发布流水线上传成功再转 published。与软件级 manifest、README 状态列一致。）
