# weplab 0.1.5 — 适配记录

## 源码信息

- 源码 URL：https://snapshot.debian.org/archive/debian/20200417T000000Z/pool/main/w/weplab/weplab_0.1.5.orig.tar.gz
- SHA256：91e4425f474d5b3213effc6d532aa3ee2fb121a1942e43c08210780a4759a72b
- MD5：713870965447b0b8b7341409968846fb
- 构建系统：autotools（configure.ac + Makefile.am，automake 1.4-p6）
- 依赖：libpcap/1.10.6

## 对话记录

### 对话 #1 [2026-09-29]

- **问题**: 加载编译 SKILL，目标库 weplab 0.1.5，在 HarmonyOS PC aarch64 上完成完整适配
- **操作**: 创建 conanfile.py、patches/、test_package/ 等完整配方结构；修复 configure.ac 的 gcc 架构标志块；修补 config.sub 识别 `aarch64-linux-ohos` triplet；绕过 make 直接编译以规避 automake-1.4 recheck 触发的 `cat -` stdin 失败；使用 `-std=gnu89` 处理 upstream inline 函数语义；使用 `-Wl,--allow-multiple-definition` 容忍 upstream 重复全局变量定义；按 E490 恢复 autotools 脚本可执行位
- **结果**: `conan create` 全绿通过（8 个 pcap 探针 + 4 个 artifact 检查 + 3 个 loader 测试 PASS + 2 个 capability SKIP）；W3 本地 CI 全 pass；最终状态 built

### 对话 #2 [2026-09-29]

- **问题**: CI（PR #13737 构建 #64380）conan-build-test 失败：config.status 在 HMDFS/FUSE 缓存上临时目录（mktemp -d 0700）不可写，Makefile 未生成；同时按积分赛规则移除不应随 PR 提交的知识草稿文件
- **操作**: conanfile.py build() 增加 config.status 运行时修补 + 条件重跑（见问题 7）；删除 knowledge/drafts/ 下 E576-draft-8E50、E577-draft-9F21 共 4 个文件（知识要点沉淀于 manifest knowledge_gained，先例 abseil 20260526 同样仅保留 ref 引用不提交草稿文件）
- **结果**: 本地独立验证修补逻辑通过（Makefile 逐字节一致）；待 CI 复验

### 对话 #3 [2026-09-29]

- **问题**: 处理 atomgit-bot AI 代码检视意见（P2×1 + P3×3，无 P0/P1）
- **操作**:
  1. P2 — `ohos_pcap_format_probe.c` probe 7 原为无条件 PASS（`pcap_close` 返回 void，无判据）：改为真实判据——对不存在路径调用 `pcap_open_offline()` 必须返回 NULL 且填充 errbuf（即 wep.c:OpenPcapFile 依赖的失败分支），`pcap_close` 释放降级为不计数的清理；同时改正文件头探针描述。
  2. P3 — probe 5 注释与实际过滤器不符：探针整体改为覆盖 weplab **真实消费面**（全源码 grep 确认 weplab 不使用 pcap_compile；实际使用 pcap_open_live / pcap_datalink / pcap_next / pcap_loop / pcap_open_offline / pcap_dump_* / pcap_lib_version）。探针 2/4/5/6 重写为 DLT 常量判别、pcap_datalink 匹配、savefile 写入（56 字节合法文件）、离线回读同一包（caplen=16）；数量仍为 8，总计 17/15/2 不变。
  3. P3 — `test_weplab.sh` 选项表用例丢弃 `flag_rc`：退出码作为证据输出到 PASS 行（判据仍为未落入 usage()，因为需要网卡的开关会在更晚的 pcap 调用处失败，退出码本身不构成判据）。
  4. P3 — `patches/0002` 新增 case 分支不可达：删除该 hunk（详见问题 3），补丁收敛为三处修改。
  5. 同步文档：MANIFEST.yml（探针登记 + 跳过原因 + `-V` 修正）、README.md、版本级 manifest.yaml（knowledge_gained 增补 config.sub 死分支与 FUSE/mktemp 两条）。
- **结果**: 本地 conan create 复验全绿：`WEPPCAP_SMOKE_DONE passed=8 failed=0`（probe 2 dlt 105/119、probe 5 size=56、probe 6 caplen=16、probe 7 errbuf 命中）；loader 3 PASS + 2 SKIP，exit=0。config.sub 裁剪后 configure 仍输出 `aarch64-linux-ohos` 并通过。

---

## 适配问题记录

### 问题 1：configure.ac 中 x86 专属的 gcc 架构优化标志块

- **现象**：configure.ac 按 `$CC -dumpversion` 匹配 gcc 分支生成 `-march`/`-msse` 等 x86 专属优化标志。OHOS 上为 clang（报 15.0.4，不匹配任何分支），当前走 "compiler is not known" 回退路径，但未来 clang 版本变化可能意外匹配产生无效标志。
- **操作**：创建 `patches/0001-fix-gcc-arch-flags.patch`，用 `MARCH=""` 和适配注释替换整个 x86 专属标志块。
- **结果**：patch 应用成功，configure 输出 "arch optimization disabled for OHOS"。（知识草稿 E576-draft-8E50）

### 问题 2：libpcap 依赖的 -I/-L 未传递

- **现象**：Conan 2.29 的 AutotoolsToolchain 不会自动转发依赖包的 `-I` 和 `-L` 标志（E430），导致 configure 中的 `AC_CHECK_LIB(pcap, pcap_open_live)` 失败（"ERROR: You need libpcap-dev!"）。
- **操作**：`generate()` 中启用 AutotoolsDeps 生成 conanbuildenv；`build()` 中取 `self.dependencies["libpcap"]` 的 package_folder，向 configure 显式传 `CFLAGS="-I<pkg>/include"`、`LDFLAGS="-L<pkg>/lib"`、`LIBS="-lpcap"`。
- **结果**：configure 成功找到 pcap 库。

### 问题 3：config.sub（2005 年）不识别 aarch64-linux-ohos triplet

- **现象**：tarball 自带 config.sub/config.guess 过旧，`./configure` 报 "Invalid configuration 'aarch64-linux-ohos': machine 'aarch64-linux' not recognized"。
- **操作**：创建 `patches/0002-fix-config-sub-aarch64-ohos.patch`，三处修改 config.sub：maybe_os 列表加 `linux-ohos*`、valid_machine 列表加 `aarch64 | aarch64-* | aarch64be-*`、OS 别名列表加 `-linux-ohos*`。（初版还加了 case 分支 `-linux-ohos*) os=-linux`，AI 检视指出其不可达——该分支位于 `-linux*)` 之前，但 `-linux-ohos*` 已在前面的别名列表里先行匹配并 `;;`，分支永不执行；且其语义是把 OHOS triplet 映射成裸 `-linux`，与 OHOS 期望的 `-linux-ohos` 相反。已从补丁中删除，补丁收敛为三处修改。）
- **结果**：`./config.sub aarch64-linux-ohos` 输出 `aarch64-linux-ohos`；configure 输出 `checking build system type... aarch64-linux-ohos` / `checking host system type... aarch64-linux-ohos`，`AC_CHECK_LIB(pcap, pcap_open_live)` 通过。

### 问题 4：automake 1.4 的 make 触发 recheck，`cat -` 读 stdin 失败

- **现象**：configure 本身成功，但 `make` 因 `missing` 报 aclocal-1.4/automake-1.4 缺失而触发 `config.status --recheck`；conan subprocess 环境中 stdin 不可用，config.status 模板的 `cat -` 失败。此外 OHOS 沙箱（HMDFS + execve 限制）无法 execve 源码树内脚本。
- **操作**：绕过 make——从 configure 生成的 Makefile 提取 `CC`/`CFLAGS`/`LIBS`/`LDFLAGS` 与 `weplab_SOURCES`，逐文件编译后直接链接（`self.run`，conanbuild 环境）。
- **结果**：构建成功，产物 bin/weplab 正常。

### 问题 5：clang C99 下 upstream inline 函数链接失败

- **现象**：`ld.lld: undefined symbol: debug` / `IncrementKeyOptimized`——upstream 的 inline 函数跨编译单元调用，gnu89 语义依赖 gcc 默认生成外部符号，clang C99 默认不给 inline 函数生成外部位。
- **操作**：编译时加 `-std=gnu89` 恢复 gnu89 inline 语义。
- **结果**：链接通过。

### 问题 6：lld 拒绝 upstream 重复全局变量定义

- **现象**：`ld.lld: error: duplicate symbol: actualTime` 等——upstream 在 bruteforce.c/heuristics.c/dictionary.c/capture.c 等多个编译单元定义同名全局变量（actualTime/initialTime/lastTime），老 gcc 默认 `-fcommon` 容忍，clang 15 默认 `-fno-common`。
- **操作**：链接时加 `-Wl,--allow-multiple-definition` 匹配原始工具链行为。
- **结果**：链接通过。

### 问题 7：CI 工作机（HMDFS/FUSE 缓存）上 config.status 临时目录不可写，Makefile 生成失败

- **现象**：CI（PR #13737 构建 #64380）在 conan-build-test 步骤失败：`./config.status[533]: can't create ./confstatpDCCnC/subs.sed: Permission denied`，Makefile 未生成。本地（conan 缓存位于 /data 原生文件系统）从未复现。
- **根因**：autoconf 2.59 模板用 `(umask 077 && mktemp -d -q "./confstatXXXXXX")` 创建临时目录，`mktemp -d` 硬编码 0700。CI 工作机的 conan 缓存在 /storage（HMDFS/FUSE），chmod 被忽略且属主重映射，0700 目录不可写，config.status 写入 subs.sed/subs.frag/out 全部 Permission denied，Makefile 的 mv 失败。
- **操作**：`build()` 中在 configure 运行后检测 Makefile 是否缺失；缺失则对已生成的 config.status 做运行时修补——将 mktemp-0700 行替换为 `umask 022 && mkdir`（创建时即 0755，FUSE 上 chmod 无法补救，仅创建模式有效，与 E490 同理），并重跑 config.status；仍失败则抛 ConanException。
- **结果**：本地独立验证：修补后 config.status 重跑 exit 0，重新生成的 Makefile 与首次成功构建的 Makefile 逐字节一致（`diff` 为空）。

## 上游测试

无上游自动化测试套件。`make check` 解析为 `check-am: all-am`（Makefile.in 第 311-312 行），无任何测试命令；tarball 亦无 test/ 目录。上游无测试入口，test_package 为唯一可执行验证层。

## test_package 结果

- 用例数：17（4 artifact 检查 + 8 pcap 探针 + 3 loader 用例 + 2 capability 用例）
- 通过：15；跳过：2；失败：0
  - artifact 层（4 PASS）：machine=AArch64 / codesign_sections=1 / needed=libc.so（无绝对路径）/ host_prefix_leak=none
  - pcap 探针层（8 PASS，每项均有真实判据）：lib_version_present / dlt_constants_ok（ieee802_11=105 prism=119 互异正数，capture.c 判别值）/ pcap_t_created / datalink_matches（dlt=105）/ dump_write_ok（size=56 = 24+16+16，savefile 写入路径）/ offline_read_packet（回读同一包 dlt=105 caplen=16）/ offline_missing_null（NULL + errbuf 非空，wep.c:OpenPcapFile 失败分支）/ unknown_name_returns_minus1（名表边界契约）
  - `pcap_close` 释放仅作清理，因 API 返回 void 无判据而不计入通过数（AI 检视 P2 整改）
  - loader 层（3 PASS + 2 SKIP）：load-version-banner / load-version-exit-code / load-usage-option-table（rcs=-a:1 -b:1 -r:1 -y:1 -c:1 -k:1，退出码作为证据输出，判据为未落入 usage()）；SKIP：cap-live-capture（需无线网卡与 root）、cap-analyze-pcap（需有效 pcap 输入文件）
- 鸿蒙新增消费者用例：`ohos_pcap_format_probe`（8 探针）——真实运行 libpcap API，覆盖 weplab 实际消费的路径（capture.c 的 DLT 判别与 pcap_open_live/pcap_next、wep.c 的 pcap_open_offline 失败分支与 savefile 写入、main.c 的 pcap_lib_version）；为运行时探针打印 PASS/FAIL，非断言式
---

**编译结束**: 2026-09-29 13:20（AI 检视整改后复验）
**最终状态**: built
