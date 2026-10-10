# kamailio-lua 6.0.6 适配笔记（OHOS PC / aarch64-linux-ohos）

## 1. 目标库身份

| 项 | 值 |
|---|---|
| 发行版子包名 | `kamailio-lua`（Alpine `kamailio` 的 `lua` 子包 / Debian `kamailio-lua-modules`） |
| 对应上游工程 | Kamailio SIP Server 6.0.6（https://github.com/kamailio/kamailio） |
| 对应上游模块 | `src/modules/app_lua`（模块名 `app_lua`，产物 `app_lua.so`，"Lua script support"） |
| 身份依据 | `pkg/kamailio/alpine/APKBUILD`: `_mod_list_lua="app_lua"`、`lua() { _generic_pkg "Lua script support" "$_mod_list_lua"; }`；`src/Makefile.groups:123 mod_list_lua=app_lua`；`cmake/groups.cmake:244 set(MOD_LIST_LUA app_lua)` |
| 语言 | C（`app_lua/` 内 3×`.c` + 3×`.h`；无平台条件编译） |
| 构建系统 | kamailio 自有 make 体系（`src/Makefile` + `Makefile.defs` + `Makefile.modules`） |

## 2. 源码核验

| 项 | 值 |
|---|---|
| 源码 URL | `https://github.com/kamailio/kamailio/archive/refs/tags/6.0.6.tar.gz`（github.com 官方归档端点；与 codeload 同路径归档字节一致，且可命中 CI 镜像回退） |
| sha256 | `5b8cd435aa52137857bbfc27804479b687a495df5634e7d8513b3ff45e98e1b6` |
| 上游 tag | `refs/tags/6.0.6` → `ca1f198369533a29443b8e6bc7662472523a1a02` |
| 为何用仓库 tag 归档 | kamailio 官网发布包 `kamailio-6.0.6_src.tar.gz`（sha256 `32e4290c…`）**不含 `test/` 目录**（实测 0 个 `test/` 条目），而本包的上游测试入口位于 `test/unit/**`；为满足上游测试可核验性，采用官方仓库 tag 归档（7731 条目，含完整 `test/`，109 个 `test/unit` 文件 / 49 个 `.sh` 用例） |

## 3. 依赖

| 依赖 | 版本 | 类型 | 证据 | 状态 |
|---|---|---|---|---|
| lua | 5.4.8.1 | 强制第三方（唯一） | `app_lua/CMakeLists.txt:11 find_package(Lua REQUIRED)`；`app_lua/Makefile:33-68`（pkg-config `lua-5.1..lua5.4` + `-l$(LUALIB) -lm`）；源码 `#include <lua.h>/<lauxlib.h>/<lualib.h>`；`README:110-142`（liblua5.1-dev，5.2/5.3/5.4 亦可） | `conan download lua/5.4.8.1 -r=ohpcd --only-recipe` **rc=0**；`conan download "lua/5.4.8.1:*" -r=ohpcd -p "os=OHOS AND arch=armv8 AND compiler=clang"` **rc=0**（package `6b129b068851896169fae42d399fa922d239ce8a`） |
| kamailio core（`../../core/*`） | 同 tarball | 同源树内组件 | `app_lua` 源码 include `../../core/*` | 运行期由 kamailio 主程序提供导出符号，非独立第三方包 |
| 系统库 libc/libm/libdl/libpthread | 工具链 sysroot | 系统 | lua `system_libs=["dl","m"]` | 不需要单独适配 |
| pkg-config / make / clang | 构建机自带 | 构建工具 | `app_lua/Makefile:17`、`Makefile.defs` | 不需要单独适配 |

传递第三方闭包为空（`conan graph info --requires=lua/5.4.8.1` → `dependencies={}`）。

## 4. OHOS 平台适配要点（实测）

### 4.1 包内（app_lua 模块）适配面 —— 无源码补丁

1. **Lua 依赖注入**：OHOS 既无系统 liblua，也无任何 lua 的 pkg-config 文件（`pkg-config --libs lua` rc=1、`which lua-config` 未找到）。上游模块 Makefile 自身支持 `LOCALBASE` 回退分支，故以
   `LOCALBASE=<conan lua package_folder>` 显式注入头/库路径，并以 `PKG_CONFIG_LIBDIR=<空目录>` 保证不会误用宿主探测结果。
2. **模块与 core 口径一致性（关键）**：kamailio 加载模块时会做两项校验——
   `ksr_version_control()` 比较 `aarch64/<os>` 目标标识 **和** 编译标志集合。模块与 core 不一致时直接拒绝加载：
   - 实测①：模块以 OS 自动探测（`harmonyos`）构建 → `module version mismatch ... core: kamailio 6.0.6 (aarch64/linux); module: kamailio 6.0.6 (aarch64/harmonyos)`
   - 实测②：模块以 `OS=linux` 但未同步 core 的 `SCTP=0 / DEFS_RM=-DHAVE_RESOLV_RES` → `module compile flags mismatch ... module: USE_TCP, ..., USE_SCTP, ..., HAVE_RESOLV_RES`
   因此本配方与 OHOS 上 core 的构建口径完全对齐：`OS=linux SCTP=0 DEFS_RM=-DHAVE_RESOLV_RES`。
3. **不改源码**：`app_lua` 模块源码不含任何平台条件编译（`grep -n "__OS_\|HAVE_" app_lua/*.c|h` 命中 0），在 OHOS 工具链下可直接编译；`patches/` 为空（最小改动，R1/R4）。
4. **只构建目标模块**：`make modules modules=modules/app_lua`（build() 中无需构建 core；core 的符号在运行期由 kamailio 主程序 `RTLD_GLOBAL` 提供）。

### 4.2 为执行上游测试而做的 core（服务端）适配 —— 不属于本包产物，仅用于测试环境

> 上游 `test/unit/**` 需要完整 kamailio 主程序，以下 4 项在测试环境中实测解决，**未进入本包配方/补丁**；
> 其中 sockaddr_storage 冲突已作为知识草稿沉淀（见 §8）。

| # | 问题（首个真实错误） | 根因 | 处理 |
|---|---|---|---|
| C1 | `core/resolve.h:290:2: error: neither gethostbyname2 or getipnodebyname present` | kamailio 用 `uname -s` 判定 OS；OHOS 上是 `HarmonyOS`，无 `ifeq ($(OS), linux)` 分支 → 缺 `-DHAVE_GETHOSTBYNAME2` 等一套 linux 定义 | `make cfg OS=linux`（显式按 Linux ABI 构建，OHOS 无 harmonyos 分支） |
| C2 | `core/resolve.c:189: use of undeclared identifier '_res'` | `-DHAVE_RESOLV_RES` 为 C_DEFS 基础定义；OHOS musl libc 无 `_res`（`resolv.h` 不声明） | `DEFS_RM="-DHAVE_RESOLV_RES"`（走 `#else` 分支，运行期仅告警 "no resolv options support"） |
| C3 | `src/modules/app_lua/...` 未见；core 侧 `linux/netlink.h` 链式引入 `linux/socket.h` → `error: redefinition of 'sockaddr_storage'` | OHOS sysroot 的 `linux/socket.h` 无条件定义 `struct sockaddr_storage`，与 libc `sys/socket.h` 冲突 | `src/core/socket_info.c` 中在 netlink 头前定义 `_UAPI_LINUX_SOCKET_H` + `__kernel_sa_family_t`（`#ifdef __OHOS__` 守卫，仅作用于 netlink 引入点）**（测试环境用，未进本包补丁）** |
| C4 | sctp 相关（sysroot 无 `netinet/sctp.h`） | OHOS sysroot 不提供 SCTP 头 | `SCTP=0` |

## 5. 上游测试申报表（R51 三步法）

### 5.1 清点（适配前）

- 上游测试入口：`test/unit/Makefile`（目标 `test` = `kamailio -c` 语法检查；`all` = 依次执行 `test/unit/*.sh`）
- 用例规模：`test/unit/` 下 **49 个 `.sh`**（含 28 个 `.cfg`、若干个 `.sip` 数据文件与 `include/` 公共脚本）
- 与本包直接相关：`61.sh` + `61.cfg` + `61-message-sdp.sip` —— 加载 `app_lua.so` 并调用 `lua_dostring("…sdpops.sdp_remove_line_by_prefix…")`，是本包唯一直接覆盖 app_lua 的上游用例
- 仓库级事实：Alpine APKBUILD 标注 `options="!check" # no testsuite`；`test/README.md` 自述 "Under development (2016-06-03 OEJ)"

### 5.2 实测（全部 49 个用例逐个执行，未漏测）

- 执行口径：`cd <src>/test/unit && <interp> ./N.sh`（逐用例 120s 超时，用例间清理 kamailio 进程）
- 解释器：OHOS PC **无 `/bin/bash`**（只有 `/bin/sh`），而上游 36/49 个用例 shebang 为 `#!/bin/bash` → 按 shebang 显式选择解释器（`#!/bin/bash` → `/data/service/hnp/bin/bash`，`#!/bin/sh` → `/bin/sh`）；若直接 `./N.sh` 会因解释器缺失而 127
- 外部工具：`sipsak` 以 conan 包 `sipsak/0.9.7.1`（ohpcd 制品，rc=0）提供并加入 PATH；`nc`/`sipp`/`mysql`/`psql` 环境缺失（对应用例按上游自身逻辑 `exit 0` 跳过）
- 结果：**total=49，OK=5，FAIL=10，SKIP=34，TIMEOUT=0**（逐用例结果与根因见 `reports/test-report.md`，原始日志 `reports/upstream_tests.log`、汇总 `reports/upstream_tests_summary.tsv`）

### 5.3 回填（诚实口径）

- 5 个 OK：`1`（最小配置加载）、`3`、`9`、`24`、`60`（sdpops SDP 操作，SIP 端到端）
- 10 个 FAIL 的根因均**不属于本包产物缺陷**：
  - `5`/`7`：用例自述 "Needs a default kamailio database setup for mysql"（需运行中的 MySQL 服务）
  - `6`/`15`：加载 `2.cfg`（全模块清单）→ 需要 `dialplan`、`db_mysql` 等依赖外部客户端库的模块（OHOS 无 mysqlclient/libpq/odbc 头）
  - `8`/`10`：`kamctl`/`kamdbctl` DB 工具链（dbtext 建库 + FIFO RPC）
  - `4`：`jsonrpcs` FIFO transport 创建失败 `Can't create FIFO: Operation not permitted`（OHOS 平台限制）
  - `14`：配置加载 `mi_fifo` —— 该模块**在 6.0.6 上游已移除**（`src/modules/mi_fifo` 不存在），属用例陈旧
  - `18`：用例依赖 `id` 命令与 `-u/-g` 用户切换（OHOS 无 `id`，且平台限制 setuid/setgid）
  - `61`：**上游用例陈旧**（唯一直接覆盖 app_lua 的用例）—— 详见 §6
- 其余 SKIP 共 **34** 个，均为上游用例自身的 `check_module/check_sipsak/check_sipp/check_netcat` 守卫（缺 db_mysql/db_postgres/db_unixodbc/db_berkeley/utils/memcached/presence*/pua*/xcpp 等模块或 sipp/nc 工具）

## 6. 上游用例 61 陈旧性取证（app_lua 直接对应用例）

`61.sh`/`61.cfg` 使用 3 处**已从 app_lua 移除/改名**的 API（6.0.6 源码为唯一依据）：

| # | 用例写法 | 6.0.6 实际 | 证据 |
|---|---|---|---|
| A1 | `modparam("app_lua", "register", "sdpops")` | `register` 参数**已不存在**（现有参数仅 `load`/`reload`/`log_mode`） | `app_lua_mod.c:68-73`（`params[]`）；`README` 无 `register`；运行期实测 `parameter <register> ... not found in module <app_lua>` |
| A2 | Lua 命名空间 `sr.sdpops.…` | 6.x 为 `KSR.sdpops.…` | `app_lua_api.c:1403 luaL_openlib(L, "KSR", …)`；实测 `attempt to index a nil value (global 'sr')` |
| A3 | KEMI 函数 `sdpops.sdp_remove_line_by_prefix`（1 参） | 名称为 `remove_line_by_prefix`，且**需要 2 个参数**（prefix, media） | `sdpops_mod.c` KEMI 导出表（`str_init("sdpops"), str_init("remove_line_by_prefix")`，`SR_KEMIP_STR, SR_KEMIP_STR`）；实测 `not enough parameters for: sdpops.remove_line_by_prefix` |

→ 结论：`61.sh` 无法在上游 6.0.6 上通过，属**上游用例与实现脱节**（与 Alpine `!check`、`test/README.md` "Under development" 一致）。本包**未修改任何上游测试文件**。

## 7. 验证结果（真实命令 / 退出码）

```bash
# 1) 依赖可消费性（R36）
conan download lua/5.4.8.1 -r=ohpcd --only-recipe                                  # rc=0
conan download "lua/5.4.8.1:*" -r=ohpcd -p "os=OHOS AND arch=armv8 AND compiler=clang"   # rc=0

# 2) 真实 conan create（含 test_package 16 项断言，其中 H1/H2/H6/H7/H8 为鸿蒙特有用例）
conan create archives/k/kamailio-lua/6.0.6 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --user=ohpcd --channel=stable                                                     # rc=0

# 3) 包产物 + OHOS 构建的 kamailio core 端到端（上游 61 场景，仅修正 3 处陈旧 API）
#    模块 = conan 包产物 lib/kamailio/app_lua.so
#    ⚠️ 该 .so 的 sha256 随 conan 构建目录变化（编译含 -g，调试信息内嵌构建路径），
#       因此不以单一哈希值作为验收口径；功能等价以下列内容级断言为准（实测）：
#         H1 ELF64/AArch64/ET_DYN ｜ H2 NEEDED 仅 libc.so、无 liblua.so
#         H4 mod_register + _app_lua_exports ｜ H5 luaL_newstate + "Lua 5.4"
#         H7 aarch64/linux ｜ H8 无 USE_SCTP / HAVE_RESOLV_RES
#       且不同构建间的 .dynsym 与 dynamic 段逐字节一致（diff 实测为空）
#    -> sipsak 三个子用例 61-test0/1/2 全部返回 SIP/2.0 200 OK，SDP 按预期改写      # exit=0
```

- `conan create`：**rc=0**；`package()` 产出 `lib/kamailio/app_lua.so`（1,055,104 B）+ `licenses/COPYING`
- `conan-verify`：见 `reports/conan-verify-report.md`
- W3（finish 内嵌本地 CI，含 conan create 复跑）：见 `.ci-result.json`
- 上游测试：49/49 已执行，统计与逐项结果见 `reports/test-report.md`

## 8. 知识沉淀

- 草稿（`knowledge/drafts/`）：OHOS sysroot `linux/socket.h` 与 libc `sys/socket.h` 的 `sockaddr_storage` 重定义（netlink 引入点守卫法，E091/E119 同类）
- 建议固化的经验（本版实测）：
  1. kamailio 系（自有 make 体系）在 OHOS 上必须显式 `OS=linux`；模块与 core 的 **目标标识 + 编译标志集合** 双重校验决定了模块构建口径必须与 core 完全一致
  2. `test/unit` 用例因 `#!/bin/bash` 在无 `/bin/bash` 的 OHOS PC 上会 127，需按 shebang 选解释器

## 9. 交付物

| 文件 | 大小 | 说明 |
|---|---|---|
| `lib/kamailio/app_lua.so` | 1,055,104 B | app_lua 模块（ELF64 / AArch64 / ET_DYN，NEEDED 仅 `libc.so`，Lua 5.4.8 静态内嵌） |
| `licenses/COPYING` | 16,405 B | 上游 GPL-2.0 许可原文 |

## 10. 注意事项

- 本包产物是 kamailio 运行期 dlopen 的插件，**不可**作为链接库使用（`cpp_info.libs` 为空）；使用时需放入 kamailio 的模块目录（`$(LIBDIR)/kamailio/`）。
- 消费方的 kamailio core 必须与模块同口径构建（OHOS：`OS=linux SCTP=0 DEFS_RM=-DHAVE_RESOLV_RES`），否则 kamailio 会以 version/flags mismatch 拒绝加载。
- 可选编译面 LuaJIT（`LUAJIT=yes`）未覆盖：ohpcd 无 `luajit` 制品且上游默认 `option(LUAJIT ... OFF)`。
- 仓库既有**大小写冲突**：git index 同时含 `archives/l/libXext/`（1.7.0 等）与 `archives/l/libxext/`（1.3.6/1.3.7 等），
  而 `core.ignorecase=true` 且文件系统不区分大小写 → 任一 worktree/clone 中这两个路径的 `README.md`/`manifest.yaml`
  必然有 2 个文件显示为 modified（实测内容与 `git show HEAD:archives/l/libxext/README.md` 逐字节相同，非他人改动）。
  因此**提交必须使用显式文件白名单**（禁止 `git add -A`），否则会把这 2 个大小写冲突文件带入 PR。
- `packaging/`（release/debug tar.gz）与 `.staging-verified` 在本包**不适用**：本包走 v3.0 配方路径
  （`conanfile.py`），SKILL/finish 对此路径不要求 legacy 预编译 tar.gz；等价验证由
  `conan-verify` 的 L2/L4/L5 smoke 检查 + `test_package` 16 项断言 + 上游 61 场景端到端承担。
  CI 发布流程为 `conan upload`（release 流水线），非 tar.gz 制品。

## 11. 适配过程对话记录（关键节点，命令/原始报错/处置）

### 对话 #1 依赖核验（W0）

- 命令：`conan download lua/5.4.8.1 -r=ohpcd --only-recipe` → rc=0；`conan download "lua/5.4.8.1:*" -r=ohpcd -p "os=OHOS AND arch=armv8 AND compiler=clang"` → rc=0
- 结论：唯一强制第三方依赖可消费，无需先适配依赖（R36 不触发）。

### 对话 #2 源码与平台适配（首次真实报错）

- 首次 `make -j2`（core）报错：`core/resolve.h:290:2: error: neither gethostbyname2 or getipnodebyname present`
- 根因：`OS := $(shell uname -s ...)` 在 OHOS 上得 `harmonyos`，无专属分支 → 缺 linux 定义；处置：`make cfg OS=linux`
- 二次报错：`core/resolve.c:189: use of undeclared identifier '_res'` → 处置：`DEFS_RM="-DHAVE_RESOLV_RES"`
- 三次报错：`linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'`（经 `linux/netlink.h`）→ 处置：netlink 引入点前置 `_UAPI_LINUX_SOCKET_H` + `__kernel_sa_family_t`（`#ifdef __OHOS__` 守卫）
- 四次：sysroot 无 `netinet/sctp.h` → 处置：`SCTP=0`
- 结果：core + 137 个模块零错误构建完成（`reports/13_make_core_fix1.log`、`14_make_core_fix2.log`）

### 对话 #3 上游测试全量执行

- 首次批量执行出现 36 个 exit=127（`timeout: exec ./37.sh: No such file or directory`）→ 根因：OHOS 无 `/bin/bash`，36/49 用例 shebang 为 `#!/bin/bash`
- 处置：按 shebang 显式选解释器（`#!/bin/bash` → `/data/service/hnp/bin/bash`；`#!/bin/sh` → `/bin/sh`），并接入 conan 包 `sipsak/0.9.7.1` 提供 SIP 工具
- 结果：49/49 全量执行 → OK=5 / FAIL=10 / SKIP=34 / TIMEOUT=0（`reports/upstream_tests_summary.tsv`）

### 对话 #4 上游用例 61 陈旧性定位（app_lua 直接对应用例）

- `61.sh` 首报：`parameter <register> of type <1:string> not found in module <app_lua>`（config 解析失败）
- 去除 `register` 行后：`error from Lua: ... attempt to index a nil value (global 'sr')` → 命名空间已改 `KSR`
- 改用 `KSR.sdpops.*` 后：`attempt to call a nil value (field 'sdp_remove_line_by_prefix')` → KEMI 名改为 `remove_line_by_prefix`
- 再改后：`not enough parameters for: sdpops.remove_line_by_prefix` → 6.0.6 需 2 参
- 结论：3 处 API 脱节（A1/A2/A3），属上游用例陈旧；本包不改上游测试文件，另建修正副本做端到端验证（§5）

### 对话 #5 配方与包产物（两次真实 mismatch 修复）

- `conan create` 首错：`Package type is 'library', but no 'shared' option declared` → 处置：`package_type = "shared-library"`
- `source()` 报 `BadZipFile: File is not a zip file` → 根因：归档 URL 末段是 tag 名 → 处置：conandata 显式 `filename: kamailio-6.0.6.tar.gz`（`get()` 支持）
- **CI 首次红灯（PR #14325）**：`worker-prep/git-clone` 失败 + 归因「源码下载超时」→ 根因：CI 的 mirror-fallback 域名白名单（`ci/conan/build_and_test.sh`）只含 `github.com`，不含 `codeload.github.com`，Worker 直连 codeload 超时 → 处置：源码 URL 改用 `github.com/<owner>/<repo>/archive/refs/tags/<tag>.tar.gz`（与前者的下载字节**sha256 完全一致**，本地实测 `5b8cd435…`），保持官方源不变、不引入镜像域名
- `self.run(env={...})` 报 `AssertionError: env argument should be a list` → 处置：改为 make 命令行变量（`LOCALBASE` / `PKG_CONFIG_LIBDIR` / `CC` / `LD`）
- 端到端加载包产物报 `module version mismatch ... (aarch64/harmonyos)` → 处置：模块加 `OS=linux`
- 再报 `module compile flags mismatch ... USE_SCTP, HAVE_RESOLV_RES` → 处置：模块口径与 core 对齐 `SCTP=0 DEFS_RM=-DHAVE_RESOLV_RES`
- 结果：`conan create` rc=0（test_package 16 项断言全绿）；包产物加载进真实 kamailio 后，上游 61 场景三子用例全绿（`reports/61_e2e_evidence.log`；产物 sha256 随构建目录变化，验收口径见 §7）

### 对话 #6 门禁与收尾

- `conan-verify` 首跑 G1 失败：缺 `export_sources()` 与补丁应用调用 → 处置：补齐标准样板（无补丁实际为空操作）→ G1-G4 全 PASS
- `finish`（W3）首跑 JC 门禁失败：full 模式扫描全仓，命中**其他包**在 main 上的存量违规文件（`archives/c/cloog`、`archives/k/kics`、`archives/l/libbfio`、`archives/t/thc` 的 `.build-closed`/`.staging-verified`）
- 处置：以 PR-diff 口径（`JUNK_PR_DIFF` 指向本包 14 个待提交文件，与 CI prdiff 模式同口径）重跑 W3 → 通过；`.ci-result.json` exit_code=0
- 遗留（其他包存量，非本包引入）：main 上上述 4 个包存在 JC1/JC5 违规跟踪文件，建议另行清理
---

**编译结束**: 2026-10-02 16:43
**最终状态**: built
