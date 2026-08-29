# bsdtar-3.7.7 — libarchive 3.7.7 CLI 工具集 HarmonyOS PC 适配知识

> **Contributor**: pc1-15 | **Status**: VERIFIED DRAFT | **Updated**: 2026-08-27
> **Source event**: bsdtar 3.7.7 HarmonyOS PC 适配，PR #6160（已合并，历史路径 B 知识配对补交）

## 知识类型与提升边界

本条目是路径 B 知识库扩展草稿，不预占正式 E 编号。它只进入 `knowledge/drafts/**`，
不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，也不声称已经 promote；
是否提升及最终分类由知识库维护者和赛事评审决定。

本条目是对已合并 PR #6160 的补交：该 PR 合并时携带完整适配证据，但未包含知识库
KV/MD 配对，本次补交补齐两个同 stem 文件，内容只基于合并工作中实际验证的证据。

## 适用场景

libarchive 系 CLI 工具（bsdtar、bsdcpio、bsdcat、bsdunzip）在 HarmonyOS PC
（arm64，hmdfs 文件系统）上做 autotools 适配时，会同时命中最少四个独立维度的问题：

1. **跨平台构建系统**：`config.guess` 无法识别 HarmonyOS，configure 推断失败；
2. **文件系统差异**：hmdfs/hmfs 强制 setgid、裁剪 group/other 权限位、硬链接不支持，
   影响 configure 临时目录创建和测试套件的精确 mode 断言；
3. **依赖边界**：实际链接依赖只有 zlib + liblzma(xz)，但制品仓 zlib 版本必须是
   `-fPIC` 重建的变体，且系统 pkg-config 路径可能抢在 conan 依赖之前；
4. **测试套件**：上游 `make check` 全量执行后需要区分真实失败、平台限制失败和
   能力相关跳过，才能形成可信的适配结论。

## 问题模型

### 1. config.guess 不识别 HarmonyOS

libarchive 3.7.7 自带 config.guess（2021-10-26）没有 HarmonyOS 条目，`./configure`
无法推断目标 triplet。修复方式是在 `case $UNAME_MACHINE:$UNAME_SYSTEM:...` 分支前
新增 HarmonyOS 分支，把 `aarch64` 等机器名映射为 `${MACHINE}-unknown-linux-ohos`。
同时为稳妥起见，conan 配方显式传递 `--build=aarch64-unknown-linux-gnu`。

### 2. hmdfs 权限位差异与 configure 临时目录

hmdfs 下创建目录时 umask 077 生效会导致 configure 的
`Create a (secure) tmp directory for tmp files` 步骤报 `Permission denied`
（E011 同类问题）。修复为 umask 002。注意本补丁修改的是**生成的 configure 文件**，
不是 configure.ac，需要与 conan 配方的 patch 机制配合。

### 3. 测试断言：assertion_file_mode 只比较 owner 位

test_main.c 的 `assertion_file_mode` 原断言精确匹配完整 mode。hmfs 强制 setgid
并裁剪 group/other 权限位，精确 0755 断言必然失败。修复是额外增加
`(mode & 0700) == (expected_mode & 0700)` 的 owner-bits-only 比较分支，保持断言
有意义的同时容忍平台权限位差异。该函数在 3.7.7 与 3.8.7 中位置不同，补丁需
按版本手动适配上下文。

### 4. 依赖边界冻结

OHOS 环境实际检测到的链接依赖只有 zlib + liblzma(xz)，bzip2/zstd/lz4/openssl/
libxml2 均未检出。关键点：

- 必须使用 `zlib/1.3.1.1`（`-fPIC` 重建版）而不是上游 `zlib/1.3.1`：
  非 PIC 的 libz.a 链接共享库时在 aarch64 上触发
  `relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol 'z_errmsg'`。
  给 zlib/1.3.1 传 `options={"fPIC": True}` 无效——该 recipe 的 `config_options()`
  删除了 fPIC 选项。
- `--without-xml2`：libxml2 是不可缺少的可选依赖（仅 xar 格式），不在 conan
  依赖图中，链接会引入不可控系统库。
- xz 的 pkg-config 命中了 harmonybrew 系统共享库（liblzma.so.5），其路径在 conan
  依赖之前，导致 conftest 链接共享库而后在运行时 rpath 找不到。对策是在
  `generate()` 中把 conan 依赖的 include/lib 路径通过 `extra_cflags`/
  `extra_ldflags` 前置，让头文件查找和链接都优先 conan 静态库。

### 5. 全量 make check 与分类统计

`make check` 保留全部 5 套件共 801 条注册项，不接受平台宏整体跳过。实测分类：

| 套件 | 运行 | 失败 | 跳过 |
|------|------|------|------|
| libarchive_test | 637 | 8 | 205 |
| bsdtar_test | 73 | 22 | 10 |
| bsdcpio_test | 49 | 8 | 9 |
| bsdcat_test | 18 | 0 | 2 |
| bsdunzip_test | 24 | 1 | 0 |
| **合计** | **801** | **39** | **226** |

失败原因全部对应已知平台限制：hmdfs 硬链接不支持（E079）、权限位差异
（E011/E129）、加密 backend 未编译（bsdunzip 的 test_P_encryption）。这些是
平台限制而非库缺陷，逐个记录类别并继续，不阻塞适配结论。

## 推荐方法

1. **config.guess 增量补丁**：用 patch 在 case 前加 HarmonyOS 分支，同时显式传
   `--build` 兜底。
2. **双权限补丁**：configure 临时目录 umask 077→002 + test_main.c 断言改为
   owner-bits-only 比较；补丁 0001/0002 按版本重新评估 clean apply，0003 需要
   按版本手动定位函数。
3. **冻结依赖**：`zlib/1.3.1.1` + `xz/5.6.2` 为唯一强制依赖，`--without-xml2`，
   generate() 中 conan include/lib 路径前置。
4. **测试分类报告**：保留 801 条注册项全量执行，失败按平台限制类别单独记录。
5. **test_package 三件套**：`bsdtar --version`（确认 zlib/1.3.1 liblzma/5.6.2
   版本串）、内存 tar 读取（libarchive 库 API）、tar 创建-提取往返（CLI 完整性）。

## 与已有知识的差异

- E007 记录 config.guess HarmonyOS 识别，本条目补充完整建立的 triplet 分支和
  `--build` 双保险及补丁回归注意。
- E011 记录 hmfs umask 077 的 Permission denied，本条目落实为 configure 临时
  目录补丁与测试阶段 umask 022 的组合做法。
- E129 记录 hmfs 权限位不完整，本条目给出 assertion_file_mode 的
  owner-bits-only 比较实现和版本差异提示。
- E079 记录 HMDFS 硬链接不支持，本条目给出其在 make check 分类统计中的对应
  失败条目（bsdtar/bsdcpio hardlink 用例）。
- E041（automake 级联重生成）与 E005（zlib -fPIC 静态库）在本条目中作为
  依赖边界冻结的具体落地（时间戳规避 + zlib/1.3.1.1 版本选择）。

本条目把这些分散条目串成 libarchive 系工具在 HarmonyOS PC 上的完整适配闭环：
构建系统感知 → 文件系统兼容 → 依赖冻结 → 测试可信分类 → 交付验证。

## 禁止做法

- 不要用平台宏整体跳过或删除上游测试注册项（掩盖回归）。
- 不要跳过 `make check`（全量 L1 证据的唯一来源）。
- 不要用非 `-fPIC` 的 zlib 版本（触发 aarch64 重定位错误）。
- 不要启用 `--with-xml2` 或引入 conan 依赖图外的系统库。
- 不要删除或覆盖已合并 PR #6160 的配方/补丁/测试文件。

## 已验证示例

bsdtar 3.7.7 在 HarmonyOS PC（arm64，clang，hmdfs/hmfs）上完成 autotools 适配：
三个补丁全部生效，`configure --build=aarch64-unknown-linux-gnu --without-xml2`
成功，`make check` 5 套件 801 条全量执行（39 failed / 226 skipped，均为已分类
平台限制），`make install` 产出 libarchive 库与四个 CLI 工具。

test_package 验证结果：

| 测试 | 结果 |
|------|------|
| bsdtar --version | bsdtar 3.7.7 - libarchive 3.7.7 zlib/1.3.1 liblzma/5.6.2 |
| tar 创建+提取往返 | 通过（内容匹配） |
| 内存 tar 库读取 | 通过（test bsdtar 3.7.7: OK） |

源码 SHA256：`879acd83c3399c7caaee73fe5f7418e06087ab2aaf40af3e99b9e29beb29faee`。
生产 CI（PR #6160 对应流水线）L0/L1 与 Conan test_package 均通过后合入 main。

## 证据来源

- `archives/b/bsdtar/3.7.7/conanfile.py`（依赖冻结、generate() 路径前置）
- `archives/b/bsdtar/3.7.7/notes.md`（适配过程、make check 五套件分类）
- `archives/b/bsdtar/3.7.7/manifest.yaml`（依赖、补丁清单、知识引用）
- `archives/b/bsdtar/3.7.7/patches/0001-build-autoconf-config.guess.patch`
- `archives/b/bsdtar/3.7.7/patches/0002-configure.patch`
- `archives/b/bsdtar/3.7.7/patches/0003-test-utils-test-main-mode.patch`
- `archives/b/bsdtar/3.7.7/test_package/conanfile.py`、`test_libarchive.c`
- GitCode PR #6160（`【知识库扩展】feat(bsdtar): 3.7.7`，已合并）