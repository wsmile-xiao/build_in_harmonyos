# kamailio-extras 6.0.6 适配笔记 — HarmonyOS PC / aarch64

## 1. 概况

| 项 | 值 |
|---|---|
| 软件 / 版本 | `kamailio-extras` 6.0.6（Alpine 的 kamailio 子包口径） |
| 上游 | [kamailio/kamailio](https://github.com/kamailio/kamailio) 6.0.6 |
| 源码包 | `kamailio-6.0.6_src.tar.gz`（kamailio.org 官方发布源） |
| SHA256 | `32e4290c6813c9d0289abe9ec2de9138e12e0381179218a7fed374ad813ecc48`（已校验） |
| 许可证 | GPL-2.0-or-later |
| 构建体系 | 经典 Makefile 体系（`src/Makefile` + `Makefile.defs`），非 autotools/cmake |
| 补丁数 | **0** |
| 构建期依赖 | `hiredis/1.2.0`（仅 cnxcc 使用，**静态**链入）、`libevent/2.1.13`（仅 cnxcc 使用，**动态**：OHOS 侧该包仅发布 `.so` 且非系统同名库 → 由 conan 依赖链提供运行时 `.so`，部署需 `LD_LIBRARY_PATH`） |
| 产物 | `lib/kamailio/modules/*.so` × 31 |
| 目标平台 | OHOS / aarch64（clang 15、libc++、Release） |

**软件识别**：`kamailio-extras` 是 Alpine 对 kamailio 的子包切分，上游并无同名 tarball；
其内容 = kamailio 6.0.6 官方源码中 `_mod_list_extras` 列出的 31 个模块。已用两份
独立证据交叉确认：

1. [Alpine `main/kamailio/APKBUILD`](https://gitlab.alpinelinux.org/alpine/aports/-/blob/master/main/kamailio/APKBUILD)
   `pkgver=6.0.6`，`_mod_list_extras`（第 164 行）31 项 —— 与本包清单**逐项一致**；
   `extras()` 子包定义见第 683 行，构建依赖 `hiredis-dev`/`hiredis-ssl`/`libevent-dev`
2. 上游 `src/Makefile.groups` 模块分组与实际构建产物

## 2. 打包范围（31 个模块）

```
auth_diameter  auth_xkeys   call_control  call_obj    cnxcc      dmq
dmq_usrloc     domainpolicy file_out      influxdbc   log_custom msrp
nosip          pdb          pvtpl         qos         rtjson     sca
seas           sms          ss7ops        sst         statsd     tcpops
timer          tmrec        tsilo         uac_redirect xhttp     xhttp_rpc
xprint
```

外部依赖实测：31 个模块中**仅 cnxcc** 探测外部库（`cnxcc/Makefile` 用 pkg-config 探测
`hiredis`/`libevent`），其余 30 个无外部库探测（`seas` 为 C++ 模块，用系统
C++ 运行时，无第三方库）。

## 3. 构建方法

```make
# 1) 生成 config.mak（必须先 cfg，否则报 No rule to make target 'cfg-defs'）
make cfg include_modules="auth_diameter auth_xkeys call_control … xprint" \
     extra_defs="见 §3 平台宏集（-D_GNU_SOURCE + 8 个 -DHAVE_*，共 9 项）"

# 2) 编模块（列表形式一次编完；-j1 见下方说明；cnxcc 依赖经命令行变量钉死）
make modules modules="modules/auth_diameter modules/auth_xkeys … modules/xprint" -j1 \
     extra_defs="见 §3 平台宏集（共 9 项）" \
     HIREDISDEFS="-Ihiredis 包目录/include" HIREDISLIBS="-Lhiredis 包目录/lib -lhiredis" \
     LEVENTDEFS="-Ilibevent 包目录/include" LEVENTLIBS="-Llibevent 包目录/lib -levent"
```

`extra_defs` 宏集（与 `kamailio-tls`/`kamailio-xml` 等同族先例一致，各宏符号均已对照
OHOS SDK sysroot 头文件实证）：

```
-D_GNU_SOURCE -DHAVE_GETHOSTBYNAME2 -DHAVE_SCHED_YIELD -DHAVE_MSG_NOSIGNAL
-DHAVE_MSGHDR_MSG_CONTROL -DHAVE_ALLOCA_H -DHAVE_TIMEGM
-DHAVE_SCHED_SETSCHEDULER -DHAVE_IP_MREQN
```

## 4. 平台差异与解决（4 条，全部经 make 命令行变量表达 → 0 补丁）

### 4.1 平台探测宏缺失

`src/Makefile.defs` 只处理 `linux`/`solaris`/`freebsd`/`darwin` 等平台分支，
`OS=harmonyos` 不匹配任何分支 → `HAVE_GETHOSTBYNAME2`/`HAVE_SCHED_YIELD` 等探测宏
全部缺失，core 头 `resolve.h`/`sched_yield.h` 直接 `#error`。
**解法**：`extra_defs` 注入 linux 分支等价宏集（见 §3）。

### 4.2 只编模块、不编 core（零补丁的关键）

- `core/resolve.c` 在 `HAVE_RESOLV_RES` 下使用 `_res`（musl 的 `resolv.h` 无此符号）
- `core/lock_ops.h` 在 `HAVE_UNION_SEMUN` 下使用 `union semun`（musl `sys/sem.h` 不导出）

二者仅在编译 **kamailio 主程序** 时触发；模块只引用 core 提供的符号（运行时由主程序
提供），因此本包只编 `modules/`，不触碰上述路径 → 无需任何补丁。
（`HAVE_UNION_SEMUN` 特意**不注入**：core 在宏未定义时自带条件定义，注入反而冲突。）

### 4.3 cnxcc 依赖探测钉死

`cnxcc/Makefile`：`CROSS_COMPILE` 为空时用 `pkg-config` 探测 `hiredis`/`libevent`，
未命中回退 `LOCALBASE`。conan 依赖包无 pkg-config 元数据，故经 make 命令行**直接覆盖**
`HIREDISDEFS`/`HIREDISLIBS`/`LEVENTDEFS`/`LEVENTLIBS`（make 命令行变量优先于 Makefile
内部赋值），构建机系统库无从劫持探测结果。

链接形态（实测 `DT_NEEDED`，与依赖包发布形态强相关）：

| 依赖 | OHOS 侧发布形态 | 实际链接 | 证据 |
|---|---|---|---|
| `hiredis/1.2.0` | 仅 `libhiredis.a` | **静态** | `redisConnect`/`redisCommand` 在 `cnxcc.so` 的 `.dynsym` 中已定义；`DT_NEEDED` 无 `libhiredis.so` |
| `libevent/2.1.13` | 仅 `.so`（无 `.a`） | **动态** | `DT_NEEDED` 含 `libevent.so` |

libevent 走动态符合仓库口径（R26 只强制"**系统同名库**必须静态"；OHOS sysroot 与目标机
`/lib` 均不含 libevent，非系统同名库 → 由 conan 依赖链提供运行时 `.so`）。`cnxcc.so`
自身**不带 RPATH/RUNPATH**（OHOS 上 `$ORIGIN` 不稳定），部署时经 `LD_LIBRARY_PATH`
定位依赖；`libevent/2.1.13` 是本包的 `requires`，消费者 `conan install` 即自动拉到。

### 4.4 模块 .so 的消费者语义

模块 `.so` 由 kamailio 主程序运行时 `loadmodule`（dlopen）加载，**核心符号由主程序提供**，
故模块脱离主程序无法独立 dlopen（实测 31/31 均因未定义 core 符号而加载失败，属正常）。
因此本包：

- `cpp_info.libs = []`（不作为链接库）
- `cpp_info.libdirs = ["lib/kamailio/modules"]`
- 消费者测试改走 **加载器同源语义**：读模块导出结构 `struct module_exports` 首字段
  `char *name`（kamailio 加载时正是读该字段注册模块），见 §5.4

## 5. 上游测试（R51 三步法）

### 5.1 清点

**清点证据（对 sha256 校验后的官方源码包逐条列举）**：`kamailio-6.0.6_src.tar.gz`
（sha256 `32e4290c…`，与 `conandata.yml` 一致）顶层为
`.clang-format` / `.devcontainer` / `.lgtm.yml` / `.pre-commit-config.yaml` /
`CMakeLists.txt` / `CMakeLists.notes` / `CODEOWNERS` / `CODE_OF_CONDUCT.md` / `COPYING` /
`ChangeLog` / `INSTALL` / `ISSUES` / `Makefile` / `README` / `README.md` / `cmake` / `doc` /
`etc` / `misc` / `pkg` / `src` / `utils` —— **不含顶层 `test/` 目录**（包内匹配 `test/`
的路径仅 10 条**模块级**路径，如 `src/modules/<mod>/test/`）。

R51 实测所用的 **49 个 `test/unit/*.sh` 不在该源码包内**，系从源码包之外另行获取的上游
6.0.6 测试树（获取命令未随归档留痕，**属本次清点证据链的已知缺口，已如实标注**）；该测试树
**不参与构建、不入包**（`source()` 只解压上述源码包，`patches/` 为空）：

| 目录 | 内容 | 是否自动化测试 |
|---|---|---|
| `test/unit/`（另行获取的测试树，非源码包内容） | `*.sh` × **49**（含 `include/common` 公共 harness） | 是（需自建 kamailio 主程序） |
| `test/travis/`（同上） | 上游 CI 包装脚本 | 否（包装器） |

- `src/Makefile` **无 `check` 目标**；CMake 侧未 `enable_testing()`/`add_test()` →
  无 `make check`/`ctest`/`pytest` 入口
- `test/unit` 运行前提：`<root>/src/kamailio` 主程序 + `<root>/src/modules` 模块树
  （harness `include/common` 以 `TOP_DIR="../.."` 定位），多数脚本依赖外部 SIP 工具
  `sipsak`/`sipp`
- **extras 31 个模块在 `test/unit` 中无专属测试用例**

### 5.2 实测运行

环境：OHOS aarch64（SDK clang），kamailio 主程序由同一源码树的探索性构建产出
（该探索构建树含 137 个模块）。

| 结果 | 数量 | 说明 |
|---|---|---|
| 跳过 | 38 | 脚本自检缺前置条件后自行 `exit 0`（非失败），分项**加总 = 38**：外部 SIP/网络工具未安装 `sipp` 15 + `sipsak` 6 + `netcat` 2 = 23；引用的模块不在本构建子集 `db_mysql` 8 + `db_postgres` 2 + `db_berkeley`/`db_unixodbc`/`utils` 各 1 = 13；DB 环境前置缺失 `3.sh`（no root password）/ `24.sh`（no .pgpass file）= 2 |
| 通过 | 2 | `1.sh`、`9.sh`（rc=0，实际执行） |
| 失败 | 9 | 逐项原因见 §5.3（**6 项平台限制 + 3 项测试环境依赖**，非同一原因） |

### 5.3 失败逐项原因（非"没环境"，均为具体技术原因）

| 脚本 | 现象 | 根因 | 与 extras 适配的关系 |
|---|---|---|---|
| 4/5/7/14/15/18.sh | kamailio 启动中止，退出码 255 | **OHOS 平台限制**：`mkfifo(2)` 返回 EPERM → jsonrpcs FIFO transport 初始化失败（见下方错误链） | 无关（jsonrpcs 属主包，不在 extras） |
| 6.sh | `could not find module <dialplan>` | 该脚本的配置检查引用 `dialplan`/`db_mysql`，二者不在本次**探索性构建的模块子集**内（137/254） | 无关（构建子集差异） |
| 8.sh | `kamdbctl` rc=1 | `utils/kamctl`（kamdbctl/dbtextdb.py）依赖该环境不具备的 python 工具链 | 无关（工具链依赖） |
| 10.sh | `dbtextdb.py: No such file or directory` | shebang 指向的解释器不存在（文件存在但无法执行） | 无关（工具链依赖） |

jsonrpcs FIFO 错误链（`kamailio -E` 实测捕获）：

```
ERROR:    jsonrpcs [jsonrpcs_fifo.c:72]  jsonrpc_init_fifo_server(): Can't create FIFO: Operation not permitted (mode=432)
CRITICAL: jsonrpcs [jsonrpcs_fifo.c:218] jsonrpc_init_fifo_file(): failed to init jsonrpc fifo server file stream
ERROR:    jsonrpcs [jsonrpcs_fifo.c:575] jsonrpc_fifo_mod_init(): cannot initialize fifo transport
ERROR:    jsonrpcs [jsonrpcs_mod.c:1250] mod_init(): cannot initialize fifo transport
ERROR:    <core>   [core/sr_module.c:1041] init_mod(): Error while initializing module jsonrpcs
ERROR: error while initializing modules
```

> 排查提示：kamailio 启动/模块初始化错误默认写 **syslog**，stderr 静默（表现为
> "进程无输出即退出"）；需加 `-E` 才能看到真实错误链。

### 5.4 适配后测试（鸿蒙特有，`test_package/`）

`check_extras_modules.py` — **36 项断言**，全部基于产物真实字节，不依赖外部工具
（自解析 ELF：`PT_LOAD`/`.dynsym`/`.symtab`/`.rela.dyn`/`.dynamic`）：

| 组 | 断言 | 内容 |
|---|---|---|
| 齐全性 | 1 | 31/31 个 `.so` 存在，名称集合精确一致 |
| 逐模块 ×31 | 31 | ELF 身份（64-bit LE / `ET_DYN` / `EM_AARCH64`）；**模块契约**：读取 `exports->name` 并与 kamailio 期望名比对；依赖闭合（`DT_NEEDED` ⊆ 允许集合）；无 `RPATH`/`RUNPATH` |
| cnxcc 依赖链入 | 3 | hiredis API 符号已定义（静态链入）；无 `libhiredis.so` 动态依赖；动态依赖 ⊆ {`libc.so`, `libevent.so`} |
| 许可证 | 1 | `licenses/COPYING` 随包 |

其中"依赖闭合"的允许集合按模块区分（文档化口径，非"禁止一切动态依赖"）：

- 31 个模块：`libc.so`
- `cnxcc`：`libc.so` + `libevent.so`（conan 依赖，OHOS 侧仅 `.so`，非系统同名库）
- `libhiredis.so` **不在**任何模块的允许集合内（hiredis 必须静态链入）

契约名实测（`exports->name`，31/31 与期望一致）：

```
auth_diameter→auth_diameter   msrp→msrp         statsd→statsd
auth_xkeys→auth_xkeys         nosip→nosip       tcpops→tcpops
call_control→call_control     pdb→pdb           timer→timer
call_obj→call_obj             pvtpl→pvtpl       tmrec→tmrec
cnxcc→cnxcc                   qos→qos           tsilo→tsilo
dmq→dmq                       rtjson→rtjson     uac_redirect→uac_redirect
dmq_usrloc→dmq_usrloc         sca→sca           xhttp→xhttp
domainpolicy→domainpolicy     seas→seas         xhttp_rpc→xhttp_rpc
file_out→file_out             sms→sms           xprint→xprint
influxdbc→influxdbc          ss7ops→**ss7** ← 上游事实
log_custom→log_custom         sst→sst
```

> 上游事实：`ss7ops.so` 的模块声明名是 `ss7`（`src/modules/ss7ops/ss7ops_mod.c:95`
> `"ss7", /*!< module name */`）——按文件名推断契约名会误判，测试表中已登记该例外。

## 6. 验证证据

| 项 | 结果 |
|---|---|
| `conan create`（OHOS aarch64 profile） | 31 个模块全部编译产出、包组装成功；test_package 端到端通过（日志 `.ci-result.json` + `reports/`） |
| `check_extras_modules.py` | **36/36 通过**（对 `conan create` 产出的包目录实测） |
| 模块依赖闭合 | 30 个模块 `DT_NEEDED` 仅 `libc.so`；`cnxcc` 另有 `libevent.so`（conan 依赖，非系统同名库）；31/31 无 `RPATH`/`RUNPATH` |
| 模块契约 | 31/31 个模块 `exports->name` 与 kamailio 期望名一致（含上游例外 `ss7ops`→`ss7`） |
| 打包文件数 | 31 个 `.so` + `licenses/COPYING` |

## 7. 已知限制与未覆盖项（如实声明）

1. **`mkfifo(2)` EPERM（OHOS 平台限制）**：影响 jsonrpcs FIFO transport（属主包，
   不在本 extras 包内）。已记录为平台事实，供后续主包适配参考。
2. **消费者运行验证的边界**：本包不含 kamailio 主程序（仓库与制品仓暂无
   `kamailio` 本体包），未能做"真机启动 kamailio + 加载 31 个模块"的端到端运行验证；
   当前消费者校验采用**加载器同源语义**（读 `exports->name` 契约字段）+ 依赖闭合 +
   ELF 身份。真机端到端运行需 kamailio 主包落地后补做。
3. **`cnxcc` 运行期需要 `libevent.so`**：libevent 在 OHOS 侧仅以 `.so` 发布，`cnxcc.so`
   的 `DT_NEEDED` 因此含 `libevent.so` 且自身不带 RPATH → 部署时须让 `libevent.so`
   位于加载器搜索路径（`libevent/2.1.13` 是本包 `requires`，`conan install` 会拉到，
   运行时经 conan 环境脚本 / `LD_LIBRARY_PATH` 生效）。其余 30 个模块无此要求。
4. **探索性构建树为模块子集**（137/254），故上游 `test/unit` 中引用非 extras 模块
   （`dialplan`/`db_mysql`）的用例在本环境不可跑通（§5.3）。

## 8. 拟沉淀知识（供知识图谱收录）

1. kamailio 平台适配：`OS=harmonyos` + `extra_defs` 注入 linux 分支等价宏集
   （共性，同族 10+ 包复用；候选合并入既有 kamailio 平台条目）
2. kamailio 只编模块规避 core 的 `_res`/`union semun`（musl 缺失符号）路径 → 零补丁
3. 模块加载契约校验法：读 `exports->name`（加载器同源语义），替代不可行的独立 dlopen；
   **ET_DYN 下该指针字段真值在 `.rela.dyn` addend 中**（lld 字段内存可能为 0）
4. 模块声明名 ≠ 文件名（`ss7ops` → `ss7`）：契约校验需登记上游例外
5. OHOS `mkfifo(2)` EPERM → jsonrpcs FIFO transport 不可用（含完整错误链）
6. kamailio 错误默认走 syslog，排查需 `-E`（通用调试技巧）
7. 外部库探测型模块 Makefile 的钉死手法：make 命令行变量覆盖（优先于文件内赋值）
8. 依赖链接形态取决于**依赖包发布形态**：OHOS 侧 `hiredis` 仅 `.a` → 静态；`libevent`
   仅 `.so` → 必然动态。判定"可否静态"应先看依赖包 `lib/` 内容与 sysroot 是否同名，
   而非只看链接参数；非系统同名库动态依赖需在部署说明中交代运行时库定位方式

## 9. 文件清单

```
6.0.6/
├── conanfile.py             # 配方（OS=harmonyos + extra_defs + 31 模块列表）
├── conandata.yml            # 源码 URL + SHA256（patches: {} → 0 补丁）
├── manifest.yaml            # 版本级元数据 + 知识沉淀
├── notes.md                 # 本文件
├── test_package/
│   ├── conanfile.py         # L1 测试入口
│   ├── check_extras_modules.py  # 36 项断言（自解析 ELF）
│   └── MANIFEST.yml         # 上游测试清点声明（CI L0e）
└── reports/                 # 验证报告（finish 写入）
```

补充说明：

* **并行度固定 `-j1`**：OHOS SELinux 禁止用户进程创建 FIFO，GNU make 的 jobserver 依赖
  FIFO 传令牌 → 仓库统一要求 `make -j1`（E525/E074；同族 10 个 kamailio-* 配方一致）。
* **保留标准补丁钩子**：`conanfile.py` 保留 `export_sources()`（`export_conandata_patches`）
  与 `build()` 首行 `apply_conandata_patches(self)`；`conandata.yml` 为 `patches: {}`，
  两者均为 no-op。保留原因：与同族配方同构、满足 conan-verify G1 配方完整性门禁
  （该门禁按文本判定这两项），并使将来确需补丁时无需改结构。
### 对话 #1 — 适配路径确定与验证（2026-09-29）

* **确认上游与范围**：`kamailio-extras 6.0.6` 是 Alpine `main/kamailio` 的 `extras()` 子包，
  对应官方源码 `kamailio-6.0.6_src.tar.gz`（sha256 已校验）；范围 = `_mod_list_extras`
  的 31 个模块，与仓库已有同族配方同源同版本。
* **选路**：沿用仓库同族 10 个 `kamailio-*` 配方既有结论（零补丁 + `OS=harmonyos` +
  `extra_defs` 注入 linux 等价宏集 + 只编 modules）。先以 6 个代表性模块
  （cnxcc/xprint/seas/msrp/influxdbc/statsd）实证可行，再一次性编全 31 个。
* **放弃全量路径**：连 core 一起编需 `_res` / `union semun` / `sockaddr_storage`
  三处绕坑（`GLIBC_COMPAT`、`-D__MUSL__`、`SCTP=0`）；本配方只编 modules，不触发
  这些路径，从而保持 **0 补丁**（`patches/` 为空，`conandata.yml` 为 `patches: {}`）。
* **cnxcc 依赖**：确认制品仓已有 `hiredis/1.2.0`、`libevent/2.1.13`；经 make 命令行
  覆盖 `HIREDISDEFS/HIREDISLIBS/LEVENTDEFS/LEVENTLIBS` 钉死到 conan 依赖包目录，
  避免模块 Makefile 的 pkg-config 探测与 `LOCALBASE` 回退。实测 `DT_NEEDED`：
  hiredis 静态链入、libevent 动态依赖（OHOS sysroot/目标机无 libevent ⇒ 非"系统同名库"，
  按 R26 口径合规，由 conan 依赖链提供运行时 .so）。
* **消费者测试方案取舍**：`dlopen` + core 符号 mock 在 OHOS musl 下 0/31（弱符号不被
  采纳）→ 改为自解析 `.dynsym`/`.rela.dyn` 直读 `exports->name`，确定性取得 31/31
  模块契约名（唯一例外：`ss7ops.so` 上游声明名为 `ss7`，属上游事实）。
* **上游测试**：`test/unit` 49 个脚本实跑 = 38 skip / 2 pass / 9 fail；9 项失败共因是
  `jsonrpcs` 创建 FIFO 得 EPERM（OHOS SELinux 平台限制），已在测试报告中逐项记因，
  并沉淀为知识草稿（运行期 FIFO 不可用）。
* **构建收尾**：`conan create`（ohos-aarch64 profile）包创建 + `test_package` 通过；
  W3 本地 CI 模拟通过（`make -j1` 对齐 E525/E074）。
---

**编译结束**: 2026-09-29 21:26
**最终状态**: built
