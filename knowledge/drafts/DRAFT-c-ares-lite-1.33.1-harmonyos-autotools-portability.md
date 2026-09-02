# DRAFT-c-ares-lite-1.33.1-harmonyos-autotools-portability

## 问题 (Problem)

c-ares-lite 1.33.1（官方 c-ares v1.33.1）在 HarmonyOS PC (aarch64) 上执行
`./configure` 直接报 `configure: error: cannot guess build type; you must specify one`。
即使改用 `--build/--host` 绕过第一道门槛，后续 `config.status` 还会因 HMDFS
umask 077 报 `could not setup config files machinery` 而中断。

## 根因 (Root Cause)

1. 本机 uname 返回 `HarmonyOS`，GNU `config.guess`（c-ares 1.33.1 自带的
   Copyright 1992-2024 版本）不含 `*:HarmonyOS:*:*` 检测分支，无法产出规范三元组，
   `config.sub` 的 OS 列表也不识别 `ohos-linux`，configure 第一阶段即失败。
2. HarmonyOS 的 HMDFS 对新目录强制 setgid，`configure` 脚本里 `umask 077`
   创建的临时目录 `drwx--S---` 连属主都无法写入，`config.status` 建立
   `CONFIG_FILES` 机制时失败（E129）。

## 方案 (Solution)

对 c-ares 源码树内文件精确打 3 个 portability 补丁（已固化为
`archives/c/c-ares-lite/1.33.1/patches/` 三个 .patch，conandata.yml 声明，
conan create build() 经 `apply_conandata_patches` 应用）：

- `config/config.guess`：新增 `*:HarmonyOS:*:*` 分支，按
  `UNAME_MACHINE` 映射 aarch64/armv7/x86_64/i686 并输出
  `${MACHINE}-unknown-linux-ohos`。
- `config/config.sub`：三处——`ohos-linux)` 归一化、OS 列表加 `ohos*`、
  内核-OS 组合列表加 `linux-ohos*-`。
- `configure`：临时目录创建处 `umask 077` → `umask 022`（E129）。

## 验证 (Verification)

本机即 HarmonyOS aarch64（UNAME_SYSTEM=HarmonyOS, Kernel 1.12.0, clang 15.0.4）：

- `./configure --prefix=...` → exit 0（识别 `aarch64-unknown-linux-ohos`）
- `make -j1` → exit 0，生成 `src/lib/.libs/libcares.a` + `libcares.so.2.18.1`
  + `src/tools/adig/ahost`
- 消费者冒烟：`clang -I include test.c -o careslite_smoke libcares.a && ./careslite_smoke`
  → `c-ares version: 1.33.1` / `test c-ares-lite 1.33.1: OK`（exit 0）
- conan create / conan-verify：G0-G4 + L2/L4/L5 全部 PASS，test_package 1/1 PASS
- 源码 SHA-256（官方发布 tarball 实测）：
  `06869824094745872fa26efd4c48e622b9bd82a89ef0ce693dc682a23604f415`

## 适用边界 (Applicability / Scope)

- 适用：任何在 HarmonyOS PC 上用 autotools 构建且源码树内自带
  `config/config.guess` + `config/config.sub` 的 C/C++ 库（c-ares、
  同类含 `config/` 子目录的 autotools 项目）；补丁对源码树内同名脚本生效，
  与 `build-aux/` 布局不同（E007 针对 build-aux/）。
- 不适用：非 autotools（cmake/meson/makefile）项目；源码树内无
  `config/config.guess|config.sub` 的工程（需走 `patch-autotools-ohos.pl` 通用工具）。
- 边界：不得用 `--build/--host` 绕过（误判交叉编译导致 AC_RUN_IFELSE 全部跳过）；
  `umask` 修复只改 configure 脚本内临时目录创建段，不改变全局 umask。

## 与既有条目查重差异 (Dedup / Delta vs Existing Entries)

- E007（config.guess 无法识别 HarmonyOS）：针对 `build-aux/` 布局 + 通用
  `patch-autotools-ohos.pl`；本条补充 `config/` 子目录布局下 c-ares 1.33.1
  实际打补丁内容与 patch_ng/toybox 兼容性（补丁必须保留末尾换行，
  否则 patch_ng 报 `patch stream is incomplete`）。
- E129（HMDFS umask 077 config.status）：本条确认 `configure` 脚本内
  `umask 077→022` 的具体行位置（`mktemp -d "./confXXXXXX"` 处）与组合验证。

## 测试可移植性补充：tempnam(NULL) 与 $TMPDIR（OHOS，R15）

- **触发条件**：在 OHOS/HMDFS 上运行 c-ares 上游 `arestest`（gtest）且测试用
  `TempFile`/`TempNam` 创建临时 hosts 文件时触发；`$TMPDIR` 非空时仍落至只读 `/tmp`。
- **根因**：OHOS 上 `tempnam(NULL, prefix)` 忽略 `$TMPDIR`，回退到只读的 `/tmp`，
  导致 c-ares 上游测试 `test/ares-test.cc` 的 `TempFile`/`TempNam` 创建临时 hosts
  文件失败（20 个用例失败：16 HostAlias + 4 FileChannelTest.GetAddrInfoHosts*）。
  直接设置 `$TMPDIR=$HOME/tmp` 对未修改入口无效（tempnam 不读取该变量）。
- **最小方案**：仅测试侧补丁 `patches/0004-ares-test-tmpdir-ohos.patch`——
  `TempNam(dir, prefix)` 在 `dir == nullptr` 且 `$TMPDIR` 非空时显式把 `$TMPDIR`
  作为目录传给 `tempnam`；未设置时保留上游回退（`tempnam(NULL, ...)`）。
  不修改生产解析器/网络逻辑/断言。
- **禁止方案**：不得推广为生产库路径替换或 `file://`/绝对路径方案；不得修改生产
  解析器、网络逻辑或断言；不得在补丁/recipe/CMake/MANIFEST/草稿/日志中写入执行端
  绝对路径、`file://`、缓存、生成物或主机库路径。
- **验证**：`$TMPDIR=$HOME/tmp`（可写）下，补丁后临时文件实际落在
  `$TMPDIR`（LANDS_UNDER_TMPDIR_PREFIX 探针 exit 0）；补丁版 `arestest` 全量
  list 1111、通过 1092/失败 19——20 项临时 hosts 类全部消除（R14 39→R15 19）。
- **适用边界**：适用于在 OHOS/HMDFS 上运行 autotools 项目自带 gtest 测试、且测试用
  `tempnam` 创建临时文件的场景；`$TMPDIR` 未设置时行为与上游一致。

## 剩余平台限制（R14/R15/R16 逐入口证据）

- **chmod(file, 0) 拒绝读取语义缺失（16 项 HostAliasUnreadable）**
  - 触发条件：`HostAliasUnreadable` 用例对临时 hosts 文件执行 `chmod(fn, 0)` 后断言读拒绝。
  - 根因：OHOS/HMDFS/SELinux 上 `chmod(file,0)` 返回成功但权限仍为 **0660**、`fopen` 仍可读；
    R13 时临时文件在只读 /tmp 创建失败 → `chmod` 返回 -1。
  - 方案：**不适用**（平台语义限制）。不得通过改断言、宽泛跳过、把 SELinux 拒绝标为通过或伪造
    权限结果处理；仅可审计的平台测试沙箱可复验。
  - 验证：探针 `chmod(fn,0) rc=0 → stat 0660 → fopen SUCCESS`；补丁版全量仍 16 项失败。
  - 边界/恢复：设备提供真实 chmod(0) 拒绝读取语义（或可写 /tmp + 语义）后重跑。
- **localhost IPv6 解析链路（3 项 LiveGetLocalhostByNameV6）**
  - 触发条件：`LiveGetLocalhostByNameV6` 对 localhost 发起 AF_INET6 查询并断言返回 IPv6 地址。
  - 根因：`/etc/hosts`（HMDFS）含 `::1 localhost` 且 AF_INET6 socket 可用，但 c-ares 查询仍
    返回空（`addrs_.size()=0`、`addrtype_=-1`）——独立平台解析链路限制，非外网 DNS 问题。
  - 方案：**不适用**（平台链路限制）。不得改源码伪造 IPv6 成功、不得把外网 DNS 作为前置。
  - 验证：gtest filter 复跑 1 通过 3 失败；`/etc/hosts`→HMDFS `::1` 条目与 AF_INET6 socket 均已核验。
  - 边界/恢复：平台提供可被 c-ares 查到的 ::1 localhost IPv6 解析（或正式 hosts 覆盖机制）后重跑。

## 关键字段 (Key Fields)

- error_signature: `cannot guess build type|OS ohos not recognized|patch stream is incomplete|could not setup config files machinery|failed to create '/tmp/ares_*'|chmod(aliases.filename(), 0) Which is: -1|addrtype_ Which is: -1`
- root_cause: 见上「根因」
- solution: 见上「方案」（三补丁组合 + 补丁需以换行结尾 + 测试侧 $TMPDIR 补丁；chmod/IPv6 为平台限制无方案）
