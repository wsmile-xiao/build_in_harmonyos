# irpas 0.10 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure；捆绑 libpcap-0.4 为 autotools 但未构建）
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4 (aarch64-linux-ohos)
- 状态: built（conan-verify 全部门禁通过）

## 编译步骤

```bash
# 源码：官方 Phenoelit 站（0.10 真实官方源，SHA-256 已核验）
# https://www.phenoelit.de/irpas/irpas_0.10.tar.gz
# sha256: 6fd6dd1b5ca7eb5e3d6f2d12608a58741756eb2b080c577a322a31af1150b1ce

# 依赖（registry 预编译包，R18：
#   irpas 0.10 官方同时需要 libpcap 与 libtirpc（rpc/types.h）
conan install --requires=libtirpc/1.3.7 --requires=libpcap/1.10.6 \
    -r=ohpcd --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=default

# 主 Makefile 构建：捆绑 libpcap-0.4 不构建（OHOS musl 缺 sys_nerr/sys_errlist），
# 改用 registry libpcap/1.10.6 + libtirpc/1.3.7 头文件与库
make CC=clang CFLAGS="-Wall -g -Wunused -Wmissing-prototypes -I. -L. -I./libpcap-0.4 \
    -I<pcap>/include -I<tirpc>/include -I<tirpc>/include/tirpc -L<pcap>/lib -L<tirpc>/lib" \
    CLIBS="-lpcap -ltirpc" cdp igrp ass irdp irdpresponder itrace tctrace protos \
    netmask file2cable dfkaa netenum hsrp icmp_redirect timestamp dhcpx -j1

# 产物：16 个 CLI 程序全部构建成功；ohc-run.py conan-verify irpas 0.10 全过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 GitHub 仓库 (Obsidian-Covenant/irpas) 无 0.10 版本（仅 0.11 现代化重构版，2025-12-16） | 任务下发版本为 0.10；GitHub 仓库只发布 0.11 | 使用 Phenoelit 官方站 https://www.phenoelit.de/irpas/irpas_0.10.tar.gz 作为真实官方 0.10 源，SHA-256 核验一致 |
| 2 | 捆绑 libpcap-0.4 `./configure` 报 "can not guess host type" | 1996 年版 config.guess/config.sub 不识别 OHOS/aarch64 | 替换为现代 config.guess/config.sub 并应用 scripts/patch-autotools-ohos.pl（E007/E072 方案），config.sub 输出 aarch64-unknown-linux-ohos |
| 3 | 捆绑 libpcap-0.4 链接失败：`undefined symbol: sys_nerr, sys_errlist` | OHOS musl libc 无 sys_nerr/sys_errlist；捆绑 libpcap-0.4 为 1996 年老代码 | 不构建捆绑 libpcap-0.4，改用 ohpcd registry 已发布的 libpcap/1.10.6；Makefile 仅构建 16 个程序目标 |
| 4 | `fatal error: 'rpc/types.h' file not found` | 主程序需要 TI-RPC 头 | 依赖 registry libtirpc/1.3.7，CFLAGS 注入 `-I<tirpc>/include/tirpc` |
| 5 | `fatal error: 'net/bpf.h' file not found` | 4 个源文件 include net/bpf.h（捆绑 libpcap 头） | 保留 `-I./libpcap-0.4`（仅取头文件，不链接其库） |
| 6 | conan create source() 阶段 SHA-256 不符：计算值 a379abaf… vs 官方 6fd6dd1b… | phenoelit.de 对 .tar.gz 响应带 `Content-Encoding: gzip`，conan 的 requests 自动解压，哈希对象变成解压后内容 | conanfile.py 改用 urllib.request 手动下载（不自动解压）+ 显式 sha256 校验 + tarfile 解压 |
| 7 | conan create generate() 报 `_Component object has no attribute 'include_paths'` | 依赖对象是组件化 CppInfo | 兼容根 CppInfo 与 components：用 includedirs/libdirs（相对包路径）+ package_folder 拼接绝对路径 |
| 8 | conan create build() 报 `tools.build:compiler_executables:c` conf 不存在 | 该 conan 版本不支持子键访问 | 读取整个 dict conf 再取 `["c"]` |
| 9 | conan create build() 报 "No rule to make target 'cdp'" | basic_layout 下 build() cwd 在 build-release/，Makefile 在 source_folder | build() 内先 `cd {self.source_folder}` 再 make |

## 源码修改

- `Makefile`：`all: libpc ${PROGRAMS}` → `all: ${PROGRAMS}`（不构建捆绑 libpcap-0.4）
  （配方以显式目标 `cdp igrp ...` 构建，等价效果；源码树未做其他修改）

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| libpcap | 1.10.6 | ohpcd registry（预编译） |
| libtirpc | 1.3.7 | ohpcd registry（预编译） |

## 上游测试枚举台账

**清点方法**：解压官方 irpas_0.10.tar.gz（SHA-256 6fd6dd1b…），全目录 grep/find 测试相关入口，
检查 Makefile 全部目标（含 `check`/`test`），逐一核对是否独立上游用例并实际尝试运行。

| # | 类别 | 条目 | 是否独立上游用例 | 分类理由 | 是否实际运行 | 结果/原因 |
|---|------|------|-----------------|----------|--------------|----------|
| 1 | 用户测试源 | `tests/`、`test/`、`*test*.c`、`*_test.c` | ❌ 无 | 官方 0.10 源码树不存在任何测试目录或测试源文件 | — | 不存在（清点证据：tar 内 38 个 .c 全为工具/库源文件，无测试文件） |
| 2 | 测试框架 | CTest/Makefile `check` 目标 | ❌ 无 | 主 Makefile（35 行）仅有 all/libpc/16 程序目标/clean/realclean，无 check/test 目标；libpcap-0.4 Makefile 亦无 | — | 不存在 |
| 3 | 断言宏/注册项 | TEST_CASE / assert 宏 | ❌ 无 | 源码为 2001 年 C 网络工具，无 gtest/catch 等框架宏 | — | 不存在 |
| 4 | 样例 | examples/、sample* | ❌ 无 | tar 内无样例目录 | — | 不存在 |
| 5 | 基准 | benchmark*、perf* | ❌ 无 | 无基准程序 | — | 不存在 |
| 6 | fixture | fixture*、data/ | ❌ 无 | 无 fixture | — | 不存在 |
| 7 | 测试脚本 | *.sh / *.pl / make check 脚本 | ❌ 无 | 源码树无任何测试脚本 | — | 不存在 |
| 8 | 构建目标 | Makefile 16 个 CLI 目标 | ❌ 非测试用例 | 是交付工具（cdp/igrp/ass/irdp/irdpresponder/itrace/tctrace/protos/netmask/file2cable/dfkaa/netenum/hsrp/icmp_redirect/timestamp/dhcpx），非测试声明 | ✅ 全部构建 | 16/16 二进制构建成功 |
| 9 | 程序冒烟（usage） | 16 个 CLI 无参运行 | ⚠️ 运行验证，非上游用例 | 工具无参打印 usage（上游行为），用于验证产物可执行，不计入上游用例数 | ✅ 全部运行 | 16/16 rc=0 输出 usage（见下） |
| 10 | 捆绑依赖 | libpcap-0.4/ | ❌ 依赖源码 | 捆绑的 1996 年老 libpcap，非测试用例 | ❌ 未运行 | 不构建（见问题 3） |

### 冒烟验证（产物可执行性，非上游测试用例）

cwd: `/storage/Users/currentUser/tmp/builds/irpas-0.10.work`

| 程序 | rc | 输出摘要 |
|------|-----|----------|
| cdp | 0 | `./cdp [-v] -i <interface> -m {0,1} ...` |
| igrp | 0 | `Usage: ./igrp [-v[v[v]]] -i <interface> -f <routes file>` |
| ass | 0 | `./ass [-v[v[v]]] -i <interface> [-ApcMs] [-P IER12] ...` |
| irdp | 0 | `Usage: ./irdp [-v (useless)] -i <interface>` |
| irdpresponder | 0 | `Usage: ./irdpresponder [-v[v[v]]] -i <interface>` |
| itrace | 0 | `Usage: ./itrace [-vn] [-pX] [-mX] [-tX] -i<dev> -d<destination>` |
| tctrace | 0 | `Usage: ./tctrace [-vn] [-pX] [-mX] [-tX] [-DX] [-SX] -i<dev> -d<destin...` |
| protos | 0 | `Usage: ./protos -i eth0 -d 10.1.2.3 -v -v` |
| netmask | 0 | `Usage: ./netmask -d <destination> -t <timeout>` |
| file2cable | 0 | `./file2cable [-v] -i <interface> -f <file>` |
| dfkaa | 0 | `DFKAA - Devices Formerly Known As Ascend FX ...` |
| netenum | 0 | `Netenum ./netenum <destination> [timeout] [verbosity]` |
| hsrp | 0 | （usage 输出） |
| icmp_redirect | 0 | `./icmp_redirect [-v[v[v]]] -i <interface> [-s <source net>/<source m...` |
| timestamp | 0 | `Usage: ./timestamp -d <destination> -t <timeout>` |
| dhcpx | 0 | `./dhcpx [-v[v[v]]] -i <interface> [-A] [-D <destination ip>]` |

## 双口径统计

- **source_declared_total（源码声明测试总数）**: **0**
  - 官方 0.10 源码树无任何测试声明：无 tests/、无 *test*.c、无 TEST_CASE/断言宏、
    无 make check 目标、无测试脚本、无样例/基准/fixture（清点证据见台账 1-7 行）。
- **configured_executable_total（当前 OHOS 配置实际实例化/注册的独立可执行用例数）**: **0**
  - 上游无测试注册体系，无可实例化测试目标。
- **executed_passed_total**: **0**
- **失败数**: 0（无测试可失败）
- **未运行/未实例化数**: 0（无测试声明）
- **全量通过率**: 0/0 — 上游确无测试（R51：附清点证据，见台账）。
- **附加说明（不计入上游用例）**：16 个 CLI 工具为交付产物而非测试；16/16 构建成功、
  无参运行全部 rc=0 打印 usage（冒烟验证产物可执行性）。捆绑 libpcap-0.4 为依赖源码，未构建。

> 结论：irpas 0.10 官方发布不包含任何上游测试（2001 年老命令行网络工具）。
> 测试覆盖由 test_package 消费者用例 + 鸿蒙专项用例承担（见对应章节）。

## 验证结果

```bash
# conan-verify 8 道门禁全过（G1/G2/G3/G4/L2/L4/L5）
python3 scripts/ohc-run.py conan-verify irpas 0.10   # exit 0, PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（application，16 CLI；依赖 libpcap/1.10.6 + libtirpc/1.3.7） |
| conandata.yml | 官方 HTTPS 源 + SHA-256（6fd6dd1b…） |
| test_package/ | 消费者用例（调用公开 CLI） |
| commands.json | 软件级 CLI 声明（R38，16 个工具） |

## 注意事项

- GitHub 上游（Obsidian-Covenant/irpas）无 0.10，只有 0.11 重构版；0.10 真实官方源是 Phenoelit 站。
- phenoelit.de 对 .tar.gz 附加 `Content-Encoding: gzip`，conan tools.files.get() 会解压导致哈希校验失败，
  配方中必须用 urllib 手动下载+校验（本库已内置该处理）。
- 捆绑 libpcap-0.4（1996 年版）在 OHOS 不可用（sys_nerr/sys_errlist 缺失），必须使用 registry libpcap。
- 各工具为网络抓包/发包工具，实际发包需 root/原始套接字权限，冒烟仅验证可执行与 usage。

## 知识候选台账 + 四范围查重 + 路径判定

### 候选 C1: 服务器对 .tar.gz 附加 Content-Encoding: gzip 导致 conan get() SHA-256 校验失败
- 真实错误: `ConanException: sha256 hash failed for 'irpas_0.10.tar.gz' file. Provided hash: 6fd6dd1b… Computed hash: a379abaf…`
- 根因: phenoelit.de 对 gzip 归档响应 `Content-Encoding: gzip`（HTTP 层透明压缩语义），conan 底层 requests/urllib3 按 HTTP 语义自动解码后交付解压字节，SHA-256 计算对象变成 tar 流（a379abaf…=解压后内容哈希）而非原始 gzip 字节（6fd6dd1b…）。
- 修复: conanfile.py source() 改用 urllib.request 手动下载（不自动解压）→ 显式 sha256 校验官方字节 → tarfile 解压。
- 验证: conan-verify G2 PASS（exit 0）；curl/python urllib 三路径 hash 一致（6fd6dd1b…）。
- 适用范围: 任何上游服务器对 .tar.gz/.tgz 返回 Content-Encoding: gzip/x-gzip 的 conan 配方。
- 四范围查重:
  - 正式条目 (graph/*.kv): E406（scout 创建期 hash 多路径交叉验证）、E299（source 失败分层）——部分相关，均非本根因（HTTP 透明解压）。
  - 图谱索引 (index.tsv): 无此错误签名条目。
  - 草稿 (drafts/): `DRAFT-conan-downloader-xgzip-content-encoding.kv/.md`（blepvco：x-gzip 尺寸校验豁免缺失，方案=urllib 回退下载）与本候选高度相似；`E561-draft-4FE2.kv`（HTTP Content-Encoding 透明解压跨下载器 SHA256 不一致，morse 2.7，方案=切换无歧义归档或 pin raw 字节层）也覆盖该机理。
  - 文档 (doc/): E406.md、E299.md 相关但不覆盖透明解压哈希机理。
- 查重结论: **trigger_overlap / solution_overlap 高**——既有草稿（x-gzip、E561-draft）已覆盖"Content-Encoding 透明解压 → 哈希层错位"机理；本轮新增差异仅具体服务器头取值（gzip vs x-gzip）与 urllib 落地实现细节，未构成独立可复用新机理。
- 路径判定: **reuse_existing**（引用既有草稿，不作为本库新建草稿）。

### 候选 C2: 捆绑老版 libpcap-0.4（1996）在 OHOS musl 链接失败（sys_nerr/sys_errlist 缺失）
- 真实错误: `ld.lld: error: undefined symbol: sys_nerr / sys_errlist`（pcap_strerror 引用）
- 根因: 捆绑 libpcap-0.4 的 pcap.c 直接引用 glibc 全局 `sys_errlist[]/sys_nerr`，OHOS musl libc 不提供这两个全局符号；且该库整体为 1996 年代码，含 config.guess 不识别 OHOS 等连锁问题。
- 修复: 不构建捆绑 libpcap-0.4，改用 ohpcd registry 已发布 libpcap/1.10.6（R18 预编译优先）+ libtirpc/1.3.7。
- 验证: conan-verify G2 PASS；16 工具全部构建成功并冒烟运行。
- 适用范围: 任何携带 1996 年代捆绑第三方库（尤其 libpcap 系）的老 C 工具，在 OHOS/musl 平台构建时；以及任何引用 sys_errlist/sys_nerr 的遗留代码（musl 不导出）。
- 四范围查重:
  - 正式条目 (graph/*.kv): 未命中（无 sys_errlist/sys_nerr/musl 全局符号缺失条目）。
  - 图谱索引 (index.tsv): 未命中。
  - 草稿 (drafts/): DRAFT-cronutils（raw Makefile CLI + OHOS 签名，非本机理）——不覆盖 sys_errlist 缺失。
  - 文档 (doc/): 未命中。
- 查重结论: 未命中；机理（musl 不导出 glibc 遗留全局符号）可跨库复用、本轮已由真实日志验证。
- 路径判定: **new_draft**（路径 B，建立 .md/.kv 草稿对）。

### 候选 C3: 1996 版 config.guess/config.sub 不识别 OHOS/aarch64
- 真实错误: `configure: error: can not guess host type; you must specify one`
- 根因: 捆绑 libpcap-0.4 自带 1996 年 config.guess/sub，无 aarch64/OHOS 分支。
- 修复: 替换现代 config.guess/config.sub + scripts/patch-autotools-ohos.pl（E007/E072 方案）。
- 验证: config.sub aarch64-unknown-linux-ohos 输出正确。
- 四范围查重: **E007/E072 正式条目完全覆盖**（patch-autotools-script）。
- 路径判定: **path_a_no_knowledge**（既有知识复用，无需新建）。

### 候选 C4: conan generate() 依赖为 _Component 时无 include_paths 属性
- 真实错误: `AttributeError: '_Component' object has no attribute 'include_paths'`
- 根因: 组件化 CppInfo 用 includedirs/libdirs（相对包路径），无 include_paths/libdirs 绝对路径属性。
- 修复: 兼容根 CppInfo 与 components——用 includedirs/libdirs + package_folder 拼接绝对路径。
- 四范围查重: DRAFT-cpp-rotor（裁剪配方缺组件）、E216（GLOB 双布局）相关但非同一属性访问机理；未命中本签名。
- 路径判定: 修法属 conan 2 通用 API 细节，跨库可复用性中等，但本轮仅一次实例、无独立日志复现；**记为候选观察**，不作新建草稿（避免低价值草稿），归入 C2 草稿的关联上下文。

### 候选 C5: `tools.build:compiler_executables:c` 子键 conf 读取失败
- 真实错误: `ConanException: [conf] 'tools.build:compiler_executables:c' does not exist in configuration list`
- 修复: 读取整个 dict conf 再取 `["c"]`。
- 四范围查重: DRAFT-cronutils-1.1（配方从 compiler_executables 读 dict 取 c 键）已覆盖同修法。
- 路径判定: **reuse_existing**（既有草稿覆盖）。

### 路径 B 判定汇总
- 七轴查重（针对 C2 新建草稿）:
  - exact_duplicate: false（无同名/同签名既有条目）
  - causal_duplicate: false（无既有条目覆盖 musl 全局符号缺失根因）
  - trigger_overlap: 低（与 E406/E299 触发面部分重叠，但错误签名不同）
  - solution_overlap: 低（registry 替换 vs 多路径验证/分类诊断）
  - combination_novelty: true（musl 不导出 glibc 遗留全局符号 + 捆绑老库判定）
  - boundary_novelty: true（明确"1996 年代捆绑库在 OHOS musl 不可链接"适用边界）
  - test_migration_novelty: true（消费者/鸿蒙测试迁移到 registry libpcap 后全绿）
- 关系: similar_to: E406, E299, E561-draft | caused_by: musl 不导出 glibc 遗留全局符号 | prerequisite_of: 无 | conflicts_with: 无
- 决定: **new_draft**（知识库扩展路径 B），草稿: `knowledge/drafts/DRAFT-irpas-0.10-musl-errlist-registry-replace.kv/.md`
- 覆盖差异: 既有条目覆盖部分（无）；本轮新增部分（musl sys_errlist/sys_nerr 缺失的链接期签名 + 捆绑老库 registry 替换决策路径）。
- 适用边界/反例: 适用于 musl/OHOS 上链接期 `undefined symbol: sys_errlist/sys_nerr`；反例——glibc 环境不触发；若依赖可静态修补（如改用 strerror()）且非 1996 捆绑库，优先修补而非整体替换。
---

**编译结束**: 2026-09-16 21:35
**最终状态**: built
