# DRAFT-kamailio-6.0.6-module-core-build-parity：kamailio 模块必须与 core 同口径构建（OHOS）

> Contributor: ohc-worker | Status: Draft | Updated: 2026-10-02
> 来源：kamailio-lua 6.0.6 适配（上游 kamailio `src/modules/app_lua`）
> 对应：`knowledge/drafts/DRAFT-kamailio-6.0.6-module-core-build-parity.kv`

## 现象

在 OHOS 上构建 kamailio 子包（发行版按模块拆分的 `kamailio-*` 包，如 `kamailio-lua` = `app_lua.so`），
`conan create` 通过、包内 `.so` 结构与符号全部正常，但把该 `.so` 放入真实 kamailio 的模块目录后
启动失败：

```console
# 第 1 次（模块按 uname 自动探测 OS 构建）
ERROR: <core> [core/sr_module.c:391]: ksr_version_control(): module version mismatch for .../app_lua.so;
       core: kamailio 6.0.6 (aarch64/linux); module: kamailio 6.0.6 (aarch64/harmonyos)

# 第 2 次（模块 OS=linux，但未同步 core 的 SCTP/DEFS_RM 口径）
ERROR: <core> [core/sr_module.c:385]: ksr_version_control(): module compile flags mismatch for .../app_lua.so
module: USE_TCP, USE_TLS, USE_SCTP, TLS_HOOKS, ..., HAVE_RESOLV_RES, TLS_PTHREAD_MUTEX_SHARED
```

## 根因

1. **OS 判定**：kamailio 的 `Makefile.defs:125` 用 `OS := $(shell uname -s | sed ...)`。
   OHOS 上 `uname -s` 输出 `HarmonyOS`，Makefile.defs 只有 `linux/freebsd/darwin/solaris/...` 分支，
   `harmonyos` 落到无专属分支的默认值 → 缺少 linux 分支的一整套定义，core 编译首个错误即为
   `core/resolve.h:290:2: error: neither gethostbyname2 or getipnodebyname present`。
   → OHOS 上必须显式 `OS=linux`（OHOS 为 Linux ABI）。
2. **OHOS 额外口径**：`SCTP=0`（sysroot 无 `netinet/sctp.h`）、
   `DEFS_RM=-DHAVE_RESOLV_RES`（OHOS libc 无 `_res`，`resolv.h` 不声明）。
3. **加载期双重校验**：kamailio 的 `ksr_version_control()` 同时比较
   ① 目标标识 `kamailio <ver> (<arch>/<os>)`；② 由 `C_DEFS` 派生的编译标志集合。
   两者任一不同即拒绝加载。因此**模块"能编译"不代表"可加载"**，模块构建口径必须与 core 完全一致。

## 推荐方案（已在 kamailio-lua 6.0.6 验证）

模块的 make 变量与 OHOS 上 core 的构建口径逐项对齐：

```bash
make cfg   OS=linux SCTP=0 DEFS_RM="-DHAVE_RESOLV_RES" LOCALBASE=<lua 依赖> CC=<clang>
make modules modules=modules/app_lua OS=linux SCTP=0 DEFS_RM="-DHAVE_RESOLV_RES" LOCALBASE=<lua 依赖>
```

并在 `test_package` 增加两条"口径一致性"断言（可在建 PR 前机械拦截该类问题）：

- `strings app_lua.so` 含 `aarch64/linux`；
- `strings app_lua.so` **不含** `USE_SCTP` / `HAVE_RESOLV_RES`。

最后用真实 kamailio core 做一次加载/端到端验证（本项目用上游 `test/unit/61.sh` 场景，
修正其 3 处陈旧 API 后三子用例全绿）。

## 备选方案（改上游源码）

在 `Makefile.defs` 的 `uname -s` sed 处补 `HarmonyOS → linux` 映射，使 core/模块两侧自动一致；
代价是引入平台补丁（本包采用零补丁的最小改动口径，故未采用）。

## 反面策略

- "模块单独适配、不关心 core 标志"：模块本地可编译、CI 可绿，但装到设备后被 core 拒绝加载——
  属最坏情况（编译通过但功能全废）。
