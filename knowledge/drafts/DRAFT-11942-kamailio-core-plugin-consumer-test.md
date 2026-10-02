# DRAFT-11942: kamailio core 插件（模块 .so）的消费者测试方法

- 条目主题：为"仅输出 kamailio 模块 `.so`（不编 core）"的配方建立可复现的消费者测试范式——dlopen + 契约核验 + core 符号桩层 + 真实算法行为用例；含桩层生成的两个关键陷阱。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联 PR：#13949（feat/kamailio-ims-6.0.6）
- 关联先例：kamailio-gcrypt / kamailio-extras / kamailio-kemix / kamailio-snmpstats

## 适用场景

kamailio 家族配方只打包模块 `.so`（由 kamailio 运行时 `loadmodule` 加载），不构建主程序；上游对这些模块通常无测试（或测试需完整 kamailio 实例）。要在 CI 干净环境内自证"编出来能用"，需自建消费者测试。

## 测试范式（三层）

1. **静态契约层（纯 Python ELF 自解析，无外部命令依赖）**：ELF64/LSB/`ET_DYN`/`EM_AARCH64`；`exports` 符号存在；`DT_NEEDED` 全量归类（libc/CRT、依赖包前缀、余下 core 符号）；`RPATH/RUNPATH` 不得指向构建机路径；依赖闭包逐符号核验。
2. **端到端消费者层（C + dlopen）**：`dlopen(RTLD_NOW)` 真实模块 → `dlsym("exports")` → 校验 `module_exports_t` 描述符（前四字段 `name/dlflags/cmds/params` 与上游同构）→ 表项计数（cfg 命令/`modparam`/KEMI）→ `mod_register()` 真实调用并观察 `sr_kemi_modules_add()` 回调 → 真实算法行为用例 → `dlclose()`。
3. **桩层（core 符号）**：`-Wl,--export-dynamic` + 自建 `kamailio_core_stub.c` 提供 core 符号，使 `RTLD_NOW` 可解析。

## 关键陷阱（本包实证修复）

### 陷阱 1：符号分类不能按 `st_info`/STT 判定，要按**重定位类型**判定

用 `llvm-nm`/`readelf --dyn-syms` 的 `st_info`（FUNC/OBJECT）区分"函数"与"对象"在 OHOS clang 产物上不可靠——实测把函数判成 0 个，桩层生成后 `dlopen` 失败。正确做法：按重定位表分类（`R_AARCH64_JUMP_SLOT`/`GLOB_DAT`/`ABS64` 等）+ 排除 `NEVER_STUB`（`_init/_fini/_start/__libc_start_main/__cxa_finalize/__dso_handle/__stack_chk_fail/__stack_chk_guard`）。

### 陷阱 2：libc/CRT 前缀过滤会误伤 core 符号

按前缀（如 `fork`、`get`、`pv_`）过滤 libc/依赖符号时，会**误跳真实 core 符号**（本包误跳过 17 个，含 `fork_process` —— 被 `fork` 前缀命中）→ `dlopen` 报 `undefined symbol: fork_process`。修法：维护 `CORE_PREFIX_EXCEPTIONS` 例外表，优先于前缀规则匹配。

### 陷阱 3：`shm_malloc` 是**宏**，必须提供全局内存 API 表对象

模块内 `#define shm_malloc(s) _shm_root.xmalloc(_shm_root.mem_block, (s))`（`core/mem/shm.h`）——桩层若只提供函数式 `shm_malloc`/`shm_free` 桩，模块仍会通过 `_shm_root`（UNDEF `R_AARCH64_GLOB_DAT`）解 NULL 崩溃。修法：桩层以**对象形式**按上游 `core/mem/memapi.h` 的 `sr_shm_api_t` 布局逐字段镜像 `_shm_root`/`_pkg_root`（后端可挂 libc `malloc/free/realloc` 并计数），并把 `_shm_root`/`_pkg_root` 加入 `NEVER_STUB` 免被弱桩覆盖。

### 陷阱 4：期望值须以**源码表项计数器**校准，不靠猜

`exports->cmds` 计数含显式表项 + 宏展开项（如 `EXP_FUNC`）。期望值须用源码级计数器（扫描 `.c` 内表定义并展开宏引用、跳过注释内逗号）校准；否则会把"41 项"误判为"4 项"而调参螺旋。

## 上游测试失效时的取向

上游测试若随实现重构而失效（如 ims_ipsec_pcscf 的 `spi_list_tests.c` 引用已移除的 `spi_node_t.id`，编译不过），**不为过编译而改上游测试文件**：0 补丁路线下如实登记为上游缺陷，改由消费者测试以模块真实算法承担覆盖（本例 SPI 链表 6 组行为用例，含 NULL/空表/未命中边界）。

## 样例库（本仓库实证）

- `archives/k/kamailio-ims/6.0.6/test_package/`（`check_ims_modules.py` 208 条 + `test_ims_modules_e2e.c` 381 条 + `kamailio_core_stub.{c,h}` + `gen_core_stub.py`）
- `archives/k/kamailio-gcrypt/6.0.6/test_package/`（单模块最小形态）、`archives/k/kamailio-kemix/6.0.6/test_package/`（含 KEMI 表观测）
